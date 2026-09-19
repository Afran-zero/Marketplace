from pathlib import Path
from pyspark.sql import SparkSession

PROJECT_ROOT = Path(__file__).resolve().parents[2]
GOLD_PATH = PROJECT_ROOT / "data" / "gold"

spark = SparkSession.builder.master("local[*]").appName("InspectGold").getOrCreate()
spark.sparkContext.setLogLevel("ERROR")

df = spark.read.parquet(str(GOLD_PATH))
print(f"Total rows: {df.count()}")
print()
df.filter("symbol = 'IBM'").orderBy("price_date", ascending=False).show(10, truncate=False)
spark.stop()