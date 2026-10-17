from pydantic import BaseModel, Field, field_validator


class DirectoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Tên không được để trống.")
        return value


class DirectoryUpdate(DirectoryCreate):
    pass
