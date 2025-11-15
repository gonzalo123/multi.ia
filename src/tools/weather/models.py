from datetime import datetime

from pydantic import BaseModel, Field


# Modelos de lecturas meteorológicas
class TemperatureReading(BaseModel):
    """Lectura de temperatura a 2 metros"""
    time: datetime = Field(..., description="Timestamp")
    value: float = Field(description="Temperatura en °C")


class HumidityReading(BaseModel):
    """Lectura de humedad relativa a 2 metros"""
    time: datetime = Field(..., description="Timestamp")
    value: int = Field(..., ge=0, le=100, description="Humedad relativa en %")


class ApparentTemperatureReading(BaseModel):
    """Lectura de temperatura aparente"""
    time: datetime = Field(..., description="Timestamp")
    value: float = Field(..., description="Temperatura aparente en °C")


class PrecipitationReading(BaseModel):
    """Lectura de precipitación"""
    time: datetime = Field(..., description="Timestamp")
    value: float = Field(..., ge=0, description="Precipitación en mm")


class EvapotranspirationReading(BaseModel):
    """Lectura de evapotranspiración"""
    time: datetime = Field(..., description="Timestamp")
    value: float = Field(..., description="Evapotranspiración en mm")


class SurfacePressureReading(BaseModel):
    """Lectura de presión superficial"""
    time: datetime = Field(..., description="Timestamp")
    value: float = Field(..., gt=0, description="Presión superficial en hPa")


class MeteoData(BaseModel):
    """Modelo para almacenar datos meteorológicos"""
    temperature: list[TemperatureReading] = Field(..., description="Lista de lecturas de temperatura")
    humidity: list[HumidityReading] = Field(..., description="Lista de lecturas de humedad")
    apparent_temperature: list[ApparentTemperatureReading] = Field(..., description="Lista de lecturas de temperatura aparente")
    precipitation: list[PrecipitationReading] = Field(..., description="Lista de lecturas de precipitación")
    evapotranspiration: list[EvapotranspirationReading] = Field(..., description="Lista de lecturas de evapotranspiración")
    surface_pressure: list[SurfacePressureReading] = Field(..., description="Lista de lecturas de presión superficial")
