import uuid
from datetime import datetime, date
from typing import List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from .models import (
    User,
    Transaction,
    Prediction,
    ModelVersion,
    WeeklyReport,
    Recommendation,
    Base,
)
from .ai_service import ai_service
from .models import (
    CategorizeRequest,
    CategorizeResponse,
    SavingsPlanRequest,
    SavingsPlanResponse,
    WeeklyReportResponse,
    TransactionCreate,
    TransactionOut,
)

router = APIRouter()

# ---------------------------------------------------------------------
# Dependency – mock current user (in a real app you would use JWT auth)
# ---------------------------------------------------------------------
async def get_current_user(db: AsyncSession = Depends()) -> User:
    # For demo purposes we just fetch the first user.
    result = await db.execute(select(User).limit(1))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user

# ---------------------------------------------------------------------
# 1️⃣ CSV Upload (basic validation – no AI)
# ---------------------------------------------------------------------
@router.post("/upload-csv", status_code=status.HTTP_202_ACCEPTED)
async def upload_csv(
    user: User = Depends(get_current_user),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(),
):
    if not file.filename.lower().endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are accepted")
    content = await file.read()
    # Simple validation – ensure required columns are present
    lines = content.decode('utf-8').splitlines()
    if not lines:
        raise HTTPException(status_code=400, detail="Empty CSV file")
    header = [h.strip().lower() for h in lines[0].split(',')]
    required = {"date", "description", "amount"}
    if not required.issubset(set(header)):
        raise HTTPException(status_code=400, detail=f"CSV missing columns: {required - set(header)}")
    # Store raw CSV rows as Transaction objects (processed flag = False)
    for row in lines[1:]:
        cols = row.split(',')
        row_dict = dict(zip(header, cols))
        try:
            txn = Transaction(
                user_id=user.id,
                date=datetime.strptime(row_dict["date"].strip(), "%Y-%m-%d").date(),
                amount=float(row_dict["amount"].strip()),
                description=row_dict["description"].strip(),
                predicted_category="",
                model_version="",
                confidence_score=0.0,
                raw_csv_data=row,  # In prod you would encrypt this
                processed=False,
            )
            db.add(txn)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Error parsing row: {row}. {exc}")
    await db.commit()
    return {"status": "uploaded", "rows": len(lines) - 1}

# ---------------------------------------------------------------------
# 2️⃣ AI‑Powered Transaction Categorization (core AI endpoint)
# ---------------------------------------------------------------------
@router.post("/categorize-transactions", response_model=CategorizeResponse)
async def categorize_transactions(
    payload: CategorizeRequest = Body(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(),
):
    # Fetch unprocessed transactions for the user
    stmt = select(Transaction).where(
        Transaction.user_id == user.id,
        Transaction.processed == False,
    )
    result = await db.execute(stmt)
    transactions = result.scalars().all()
    if not transactions:
        raise HTTPException(status_code=404, detail="No unprocessed transactions found")
    # Determine which model version to log
    model_version = payload.model_version or (await db.scalar(select(ModelVersion.version).where(ModelVersion.is_active == True)))
    if not model_version:
        model_version = "default"
    # Call AI service for each description (could be batched in prod)
    categorized: List[Dict[str, Any]] = []
    for txn in transactions:
        ai_result = await ai_service.categorize(txn.description)
        category = ai_result.get("category", "Other")
        confidence = float(ai_result.get("confidence", 0.0))
        # Update transaction record
        txn.predicted_category = category
        txn.confidence_score = confidence
        txn.model_version = model_version
        txn.processed = True
        txn.processed_at = datetime.utcnow()
        # Store separate Prediction row for auditability
        pred = Prediction(
            transaction_id=txn.id,
            category=category,
            confidence=confidence,
            reason=ai_result.get("reason", {}),
        )
        db.add(pred)
        categorized.append(
            {
                "id": txn.id,
                "date": txn.date,
                "description": txn.description,
                "amount": float(txn.amount),
                "predicted_category": category,
                "confidence_score": confidence,
                "user_overridden_category": txn.user_overridden_category,
            }
        )
    await db.commit()
    return CategorizeResponse(transactions=[TransactionOut(**c) for c in categorized], model_used=model_version)

# ---------------------------------------------------------------------
# 3️⃣ Savings‑Plan Recommendations (second AI endpoint)
# ---------------------------------------------------------------------
@router.post("/generate-savings-plan", response_model=SavingsPlanResponse)
async def generate_savings_plan(
    req: SavingsPlanRequest = Body(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(),
):
    # Pull categorized transactions in the requested timeframe
    stmt = select(Transaction).where(
        Transaction.user_id == user.id,
        Transaction.date >= req.timeframe_start,
        Transaction.date <= req.timeframe_end,
        Transaction.processed == True,
    )
    result = await db.execute(stmt)
    txns = result.scalars().all()
    if not txns:
        raise HTTPException(status_code=404, detail="No transactions in the given period")
    tx_data = [
        {
            "date": txn.date.isoformat(),
            "amount": float(txn.amount),
            "category": txn.predicted_category,
        }
        for txn in txns
    ]
    ai_response = await ai_service.generate_savings_plan(tx_data)
    recommendations = ai_response.get("recommendations", [])
    model_used = ai_service.settings.model_name
    return SavingsPlanResponse(
        recommendations=[
            SavingsPlanItem(
                description=item.get("description", ""),
                confidence=float(item.get("confidence", 0.0)),
                estimated_monthly_savings=float(item.get("estimated_monthly_savings", 0.0)),
            )
            for item in recommendations
        ],
        model_used=model_used,
    )

# ---------------------------------------------------------------------
# 4️⃣ Weekly Report (non‑AI – aggregation)
# ---------------------------------------------------------------------
@router.get("/weekly-report", response_model=WeeklyReportResponse)
async def weekly_report(
    start_date: date,
    end_date: date,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(),
):
    # Aggregate spending per category
    stmt = select(
        Transaction.predicted_category,
        func.sum(Transaction.amount).label("total"),
    ).where(
        Transaction.user_id == user.id,
        Transaction.date >= start_date,
        Transaction.date <= end_date,
        Transaction.processed == True,
    ).group_by(Transaction.predicted_category)
    result = await db.execute(stmt)
    breakdown = {row[0]: float(row[1]) for row in result.fetchall()}
    total_spending = sum(breakdown.values())
    # Pull any saved recommendations (if any) – simplified
    rec_stmt = select(Recommendation).join(WeeklyReport).where(
        WeeklyReport.user_id == user.id,
        WeeklyReport.start_date == start_date,
        WeeklyReport.end_date == end_date,
    )
    rec_res = await db.execute(rec_stmt)
    recs = [
        {
            "type": r.recommendation_type,
            "description": r.description,
            "confidence": r.confidence,
        }
        for r in rec_res.scalars().all()
    ]
    return WeeklyReportResponse(
        start_date=start_date,
        end_date=end_date,
        total_spending=total_spending,
        category_breakdown=breakdown,
        savings_recommendations=recs,
        generated_at=datetime.utcnow(),
    )

# ---------------------------------------------------------------------
# 5️⃣ Delete User Data (GDPR compliance endpoint)
# ---------------------------------------------------------------------
@router.delete("/delete-user-data", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_data(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(),
):
    # Soft‑delete user – cascade deletes all related rows via ON DELETE CASCADE
    await db.execute(delete(User).where(User.id == user.id))
    await db.commit()
    return None
