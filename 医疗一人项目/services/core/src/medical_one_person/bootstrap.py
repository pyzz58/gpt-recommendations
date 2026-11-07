from __future__ import annotations

import json

from sqlalchemy.orm import sessionmaker

from medical_one_person.config import get_settings
from medical_one_person.infrastructure.bootstrap import bootstrap_local_owner
from medical_one_person.infrastructure.db.engine import create_database_engine


def main() -> None:
    settings = get_settings()
    engine = create_database_engine(settings.database_url)
    try:
        identity = bootstrap_local_owner(sessionmaker(bind=engine, expire_on_commit=False))
        print(
            json.dumps(
                {
                    "workspace_id": str(identity.workspace_id),
                    "owner_user_id": str(identity.owner_user_id),
                    "mode": "local",
                },
                ensure_ascii=False,
            )
        )
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
