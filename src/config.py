import os
from dotenv import load_dotenv

load_dotenv()

TOP_K = int(os.getenv("TOP_K", "5"))
DATA_RAW_NVD = os.getenv("DATA_RAW_NVD", "data/raw/nvd")
DATA_RAW_MITRE = os.getenv("DATA_RAW_MITRE", "data/raw/mitre")
DATA_PROCESSED = os.getenv("DATA_PROCESSED", "data/processed")
FAISS_DIR = os.getenv("FAISS_DIR", "vectorstore/faiss_index")

if __name__ == "__main__":
    print("TOP_K =", TOP_K)
    print("DATA_RAW_NVD =", DATA_RAW_NVD)
    print("DATA_RAW_MITRE =", DATA_RAW_MITRE)
    print("DATA_PROCESSED =", DATA_PROCESSED)
    print("FAISS_DIR =", FAISS_DIR)