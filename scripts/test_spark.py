from pyspark.sql import SparkSession

spark = SparkSession.builder.master("local[*]").appName("test").getOrCreate()
print("Spark session created successfully:", spark.version)
spark.stop()