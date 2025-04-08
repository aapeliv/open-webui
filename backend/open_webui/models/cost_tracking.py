import json
import time
import uuid
from typing import Optional

from open_webui.internal.db import Base, get_db
from open_webui.utils.access_control import has_access
from open_webui.models.users import User

from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Boolean, Column, String, Text, JSON, Float
from sqlalchemy import or_, func, select, and_, text
from sqlalchemy.sql import exists
import logging, sys

logging.basicConfig(stream=sys.stdout)
log = logging.getLogger(__name__)

####################
# OpenRouter generation tracking DB Schema
####################


class OpenRouterGeneration(Base):
    __tablename__ = "open_router_generations"

    id = Column(Text, primary_key=True)
    user_id = Column(Text)

    open_router_gen_id = Column(Text, index=True)

    fetched_at = Column(BigInteger, nullable=True)
    model = Column(Text, nullable=True)
    total_cost = Column(Float, nullable=True)
    # raw response from open router
    data = Column(JSON, nullable=True)

    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)


class OpenRouterGenerationModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    open_router_gen_id: str

    fetched_at: Optional[int] = None
    total_cost: Optional[float] = None
    model: Optional[str] = None
    data: Optional[dict] = None

    created_at: int  # timestamp in epoch
    updated_at: int  # timestamp in epoch


####################
# Forms
####################


class OpenRouterGenerationForm(BaseModel):
    name: str
    description: Optional[str] = None
    data: Optional[dict] = None
    meta: Optional[dict] = None
    access_control: Optional[dict] = None


class OpenRouterGenerationTable:
    def upsert_generation(
        self, user_id: str, open_router_gen_id: str
    ) -> Optional[OpenRouterGenerationModel]:
        with get_db() as db:
            existing_gen = (
                db.query(OpenRouterGeneration)
                .filter_by(open_router_gen_id=open_router_gen_id)
                .one_or_none()
            )
            if not existing_gen:
                db.add(
                    OpenRouterGeneration(
                        id=str(uuid.uuid4()),
                        user_id=user_id,
                        open_router_gen_id=open_router_gen_id,
                        created_at=int(time.time_ns()),
                        updated_at=int(time.time_ns()),
                    )
                )
                db.commit()

    def update_fetched_data(self, open_router_gen_id: str, data, total_cost, model):
        with get_db() as db:
            existing_gen = (
                db.query(OpenRouterGeneration)
                .filter_by(open_router_gen_id=open_router_gen_id)
                .one_or_none()
            )
            if not existing_gen:
                log.error(f"Didn't find gen with id {open_router_gen_id}")
                return
            existing_gen.fetched_at = int(time.time_ns())
            existing_gen.total_cost = total_cost
            existing_gen.model = model
            existing_gen.data = data
            db.commit()

    def get_all_costs(self):
        with get_db() as db:
            subq = (
                select(
                    OpenRouterGeneration.user_id,
                    func.sum(OpenRouterGeneration.total_cost).label("cumulative_cost"),
                )
                .group_by(OpenRouterGeneration.user_id)
                .subquery()
            )
            res = db.execute(
                select(User.id, User.name, User.email, subq.c.cumulative_cost)
                .join(subq, subq.c.user_id == User.id)
                .order_by(subq.c.cumulative_cost.desc())
            ).all()
            return [
                {
                    "id": user_id,
                    "name": name,
                    "email": email,
                    "total_cost": cumulative_cost,
                    "cost_by_model": [
                        {
                            "model": model or "unknown",
                            "total_cost": total_cost,
                        }
                        for model, total_cost in db.execute(
                            select(
                                OpenRouterGeneration.model,
                                func.sum(OpenRouterGeneration.total_cost),
                            )
                            .where(OpenRouterGeneration.user_id == user_id)
                            .group_by(OpenRouterGeneration.model)
                            .order_by(func.sum(OpenRouterGeneration.total_cost).desc())
                        ).all()
                    ],
                    "missing_costs": db.execute(
                        select(func.count(OpenRouterGeneration.open_router_gen_id))
                        .where(OpenRouterGeneration.user_id == user_id)
                        .where(OpenRouterGeneration.fetched_at == None)
                    ).scalar_one(),
                }
                for user_id, name, email, cumulative_cost in res
            ]


OpenRouterGenerations = OpenRouterGenerationTable()
