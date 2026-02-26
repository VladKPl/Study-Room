from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional

class LessonBase(BaseModel):
    id: int
    title: str
    video_url: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

class CategoryBase(BaseModel):
    id: int
    name: str
    model_config = ConfigDict(from_attributes=True)

class CourseBase(BaseModel):
    id: int  
    title: str
    description: Optional[str] = None 
    price: float
    category: Optional[CategoryBase] = None
    lessons: List[LessonBase] = Field(default_factory=list)
    model_config = ConfigDict(from_attributes=True)

class CourseResponse(BaseModel):
    data: List[CourseBase]
    count: int
    page: int
    page_size: int
