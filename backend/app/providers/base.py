from __future__ import annotations
from abc import ABC, abstractmethod


class FootballDataProvider(ABC):
    @abstractmethod
    async def standings(self, season: int): ...

    @abstractmethod
    async def fixtures(self, team_id: int | None = None): ...

    @abstractmethod
    async def players(self, team_id: int): ...

    @abstractmethod
    async def transfers(self): ...

    # Implement your licensed provider here. Keep API keys server-side.
