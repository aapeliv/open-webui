import json
import time
import uuid
from typing import Optional

from open_webui.internal.db import Base, get_db
from open_webui.utils.access_control import has_access

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
            log.info("trying to update?")
            existing_gen = db.query(OpenRouterGeneration).filter_by(open_router_gen_id=open_router_gen_id).one_or_none()
            log.info(f"{existing_gen=}")
            if not existing_gen:
                db.add(OpenRouterGeneration(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    open_router_gen_id=open_router_gen_id,
                    created_at=int(time.time_ns()),
                    updated_at=int(time.time_ns()),
                ))
                db.commit()


    # def get_channels(self) -> list[ChannelModel]:
    #     with get_db() as db:
    #         channels = db.query(Channel).all()
    #         return [ChannelModel.model_validate(channel) for channel in channels]

    # def get_channels_by_user_id(
    #     self, user_id: str, permission: str = "read"
    # ) -> list[ChannelModel]:
    #     channels = self.get_channels()
    #     return [
    #         channel
    #         for channel in channels
    #         if channel.user_id == user_id
    #         or has_access(user_id, permission, channel.access_control)
    #     ]

    # def get_channel_by_id(self, id: str) -> Optional[ChannelModel]:
    #     with get_db() as db:
    #         channel = db.query(Channel).filter(Channel.id == id).first()
    #         return ChannelModel.model_validate(channel) if channel else None

    # def update_channel_by_id(
    #     self, id: str, form_data: ChannelForm
    # ) -> Optional[ChannelModel]:
    #     with get_db() as db:
    #         channel = db.query(Channel).filter(Channel.id == id).first()
    #         if not channel:
    #             return None

    #         channel.name = form_data.name
    #         channel.data = form_data.data
    #         channel.meta = form_data.meta
    #         channel.access_control = form_data.access_control
    #         channel.updated_at = int(time.time_ns())

    #         db.commit()
    #         return ChannelModel.model_validate(channel) if channel else None

    # def delete_channel_by_id(self, id: str):
    #     with get_db() as db:
    #         db.query(Channel).filter(Channel.id == id).delete()
    #         db.commit()
    #         return True


OpenRouterGenerations = OpenRouterGenerationTable()
