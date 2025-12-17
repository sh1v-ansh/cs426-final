from sqlmodel import SQLModel, Field, Column
from typing import Optional, List
import json
from sqlalchemy import JSON

class Student(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    completed_courses: List[str] = Field(default=[], sa_column=Column(JSON))

class Course(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    code: str
    capacity: int
    enrolled: int = 0
    prerequisites: List[str] = Field(default=[], sa_column=Column(JSON))

class Enrollment(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    student_id: int
    course_id: int