from pydantic import BaseModel


class DashboardStats(BaseModel):
    total_images: int
    total_strains: int
    total_species: int
    total_media: int
    total_environments: int = 0


class SpeciesDistributionItem(BaseModel):
    species_name: str
    image_count: int


class MediaDistributionItem(BaseModel):
    media_name: str
    image_count: int


class StrainDistributionItem(BaseModel):
    strain_name: str
    image_count: int


class EnvironmentDistributionItem(BaseModel):
    environment_name: str
    image_count: int
