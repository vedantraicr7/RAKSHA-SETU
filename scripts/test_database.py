import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text


load_dotenv()


DATABASE_URL = (
    f"postgresql+psycopg://"
    f"{os.getenv('DB_USER')}:"
    f"{os.getenv('DB_PASSWORD')}@"
    f"{os.getenv('DB_HOST')}:"
    f"{os.getenv('DB_PORT')}/"
    f"{os.getenv('DB_NAME')}"
)


engine = create_engine(DATABASE_URL)


with engine.connect() as conn:

    result = conn.execute(
        text("SELECT PostGIS_Version();")
    )

    print(
        "PostGIS:",
        result.scalar()
    )
