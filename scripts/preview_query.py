import os
import re
from dune_client.client import DuneClient
from dotenv import load_dotenv
import sys
import pandas as pd

dotenv_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(dotenv_path)

dune = DuneClient.from_env()

ALLOWED_QUERY_PREFIX = re.compile(
    r"(?is)\A(?:\s|--[^\n]*(?:\n|$)|/\*.*?\*/)*(select|with)\b"
)
WRITE_SQL_KEYWORDS = re.compile(
    r"(?i)\b(insert|update|delete|drop|alter|create|grant|revoke|truncate|merge|call)\b"
)


def build_preview_sql(raw_query_text: str) -> str:
    normalized_query = raw_query_text.strip()
    if normalized_query.endswith(";"):
        normalized_query = normalized_query[:-1].rstrip()

    query_without_comments = re.sub(
        r"(?s)--[^\n]*(?:\n|$)|/\*.*?\*/",
        " ",
        normalized_query,
    )

    if ";" in query_without_comments:
        raise ValueError("Only a single SQL statement can be previewed.")

    if not ALLOWED_QUERY_PREFIX.match(normalized_query):
        raise ValueError("Only SELECT/WITH queries can be previewed.")

    if WRITE_SQL_KEYWORDS.search(query_without_comments):
        raise ValueError("Only read-only SQL can be previewed.")

    return f"select * from (\n{normalized_query}\n) as preview_query limit 20"


if len(sys.argv) < 2:
    raise SystemExit("Usage: python scripts/preview_query.py <query_id>")

query_id = sys.argv[1].strip()
if not query_id.isdigit():
    raise SystemExit("Query id must be numeric.")

queries_path = os.path.join(os.path.dirname(__file__), "..", "queries")
files = os.listdir(queries_path)
found_files = [
    file for file in files if query_id == file.split("___")[-1].split(".")[0]
]

if len(found_files) != 0:
    query_file = os.path.join(
        os.path.dirname(__file__), "..", "queries", found_files[0]
    )

    print("getting 20 line preview for query {}...".format(query_id))

    with open(query_file, "r", encoding="utf-8") as file:
        query_text = file.read()

    try:
        preview_sql = build_preview_sql(query_text)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    print(preview_sql)

    results = dune.run_sql(preview_sql)
    # print(results.result.rows)
    results = pd.DataFrame(data=results.result.rows)
    print("\n")
    print(results)
    print("\n")
    print(results.describe())
    print("\n")
    print(results.info())
else:
    print("query id file not found, try again")
