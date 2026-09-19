from pathlib import Path
from pyspark.sql import SparkSession

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SILVER_PATH = PROJECT_ROOT / "data" / "silver"

spark = SparkSession.builder.master("local[*]").appName("InspectSilver").getOrCreate()
spark.sparkContext.setLogLevel("ERROR")

df = spark.read.parquet(str(SILVER_PATH))

print(f"Total rows: {df.count()}")
print(f"Symbols: {df.select('symbol').distinct().count()}")
print(f"Date range: {df.agg({'price_date': 'min'}).collect()[0][0]} to {df.agg({'price_date': 'max'}).collect()[0][0]}")
print()
df.show(5, truncate=False)
print()
df.printSchema()
spark.stop()