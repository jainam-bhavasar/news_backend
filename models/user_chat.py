from typing import List, Dict, Optional
from pydantic import BaseModel, Field
from bson import ObjectId

class ChatMessage(BaseModel):
    text: str
    isUser: bool

class UserChat(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    userId: str
    articleId: str
    createdAt: str
    messages: List[ChatMessage]

    class Config:
        allow_population_by_field_name = True
        json_encoders = {
            ObjectId: str
        }

    @classmethod
    def from_mongo(cls, data: Dict) -> "UserChat":
        if not data:
            return None
        
        if "_id" in data:
            data["_id"] = str(data["_id"])
        
        return cls(**data)

    def to_mongo(self) -> Dict:
        data = self.dict(by_alias=True, exclude_none=True)
        if "_id" in data:
            data["_id"] = ObjectId(data["_id"])
        return data 