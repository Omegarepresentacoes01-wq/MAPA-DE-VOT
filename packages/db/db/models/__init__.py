"""
models — Todos os modelos SQLAlchemy da plataforma.
Importar este módulo garante que todos os models sejam registrados no metadata.
"""
from db.models.political import Person, Party, Election, Office, Candidacy  # noqa: F401
from db.models.territorial import Territory, PollingZone, PollingPlace, PollingSection, CensusSector  # noqa: F401
from db.models.analytical import VoteResult, TurnoutSummary  # noqa: F401
from db.models.financial import CampaignRevenue, CampaignExpense  # noqa: F401
from db.models.socioeconomic import (  # noqa: F401
    DemographicSnapshot,
    IncomeSnapshot,
    SocialProgramSnapshot,
)
from db.models.governance import DataSource, DatasetVersion, RecordLineage  # noqa: F401
