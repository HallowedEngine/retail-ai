# dedupe_alerts.py
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os

DB_URL = os.getenv("DB_URL", "sqlite:///./data/demo.db")
engine = create_engine(DB_URL, connect_args={"check_same_thread": False} if DB_URL.startswith("sqlite") else {})
SessionLocal = sessionmaker(bind=engine)

def dedupe():
    s = SessionLocal()
    # Bu sorgu aynı (batch_id, product_id) için en eski created_at'ı korur, diğerlerini siler.
    # SQLite için rowid yerine created_at kullanıyoruz.
    # Genel yol: önce hangi id'leri koruyacağımızı seç, sonra diğerlerini sil.
    keep_sql = """
    SELECT MIN(id) AS keep_id
    FROM expiry_alerts
    GROUP BY batch_id, product_id
    """
    keep_ids = [r[0] for r in s.execute(text(keep_sql)).fetchall()]
    if not keep_ids:
        print("Silinecek duplicate yok.")
        s.close()
        return
    # Sil: expiry_alerts tablosundaki id'leri keep_ids dışında bırak (SQL injection güvenli)
    from sqlalchemy import bindparam
    placeholders = ",".join([f":id{i}" for i in range(len(keep_ids))])
    delete_sql = f"DELETE FROM expiry_alerts WHERE id NOT IN ({placeholders})"
    params = {f"id{i}": keep_ids[i] for i in range(len(keep_ids))}
    s.execute(text(delete_sql), params)
    s.commit()
    print("Dedupe tamamlandı. Korunan kayıt sayısı:", len(keep_ids))
    s.close()

if __name__ == "__main__":
    dedupe()
