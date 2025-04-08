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

    def update_fetched_data(self, open_router_gen_id: str, data, total_cost):
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
                select(User.name, User.email, User.id, subq.c.cumulative_cost).join(
                    subq, subq.c.user_id == User.id
                )
            ).all()
            return [
                {
                    "id": user_id,
                    "name": name,
                    "email": email,
                    "cumulative_cost": cumulative_cost,
                }
                for user_id, name, email, cumulative_cost in res
            ]


OpenRouterGenerations = OpenRouterGenerationTable()
