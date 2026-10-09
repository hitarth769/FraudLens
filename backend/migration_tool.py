import sqlite3
import os
import sys
import argparse
from datetime import datetime
from typing import List, Tuple, Dict

class MigrationError(Exception):
    """Custom exception for migration failures."""
    pass

class MigrationTool:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def validate_schema(self, conn: sqlite3.Connection):
        """Ensure the required column exists in the transactions table."""
        cursor = conn.execute("PRAGMA table_info(transactions)")
        columns = [row['name'] for row in cursor.fetchall()]
        if 'recipient_account_id' not in columns:
            raise MigrationError("Schema validation failed: 'recipient_account_id' column missing in 'transactions' table.")
        if 'merchant_id' not in columns:
            raise MigrationError("Schema validation failed: 'merchant_id' column missing in 'transactions' table.")

        # Check for merchants and accounts tables
        try:
            conn.execute("SELECT 1 FROM merchants LIMIT 1")
            conn.execute("SELECT 1 FROM accounts LIMIT 1")
        except sqlite3.OperationalError as e:
            raise MigrationError(f"Schema validation failed: Missing required table. {e}")

    def backup_database(self) -> str:
        """Backup database using SQLite Backup API for WAL safety."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{self.db_path}.backup_{timestamp}.db"

        src = self._get_connection()
        dst = sqlite3.connect(backup_path)

        try:
            with src:
                src.backup(dst)

            # Verify backup integrity
            integrity = dst.execute("PRAGMA integrity_check").fetchone()[0]
            if integrity != "ok":
                raise MigrationError(f"Backup integrity check failed: {integrity}")

            # Verify record counts match for transactions
            src_count = src.execute("SELECT count(*) FROM transactions").fetchone()[0]
            dst_count = dst.execute("SELECT count(*) FROM transactions").fetchone()[0]
            if src_count != dst_count:
                raise MigrationError(f"Backup record count mismatch: src={src_count}, dst={dst_count}")

        finally:
            src.close()
            dst.close()

        return backup_path

    def classify_record(self, conn: sqlite3.Connection, record: sqlite3.Row) -> str:
        """
        Classification Logic:
        - MERCHANT_ONLY: merchant_id in merchants only.
        - ACCOUNT_ONLY: merchant_id in accounts only. (Eligible)
        - COLLISION: merchant_id in both. (Refuse)
        - UNKNOWN: merchant_id in neither. (Refuse)
        - CONFLICT: Both merchant_id and recipient_account_id populated. (Refuse)
        """
        merchant_id = record['merchant_id']
        recipient_account_id = record['recipient_account_id']

        if merchant_id is None:
            return "UNKNOWN" # Or handle as already migrated

        if merchant_id and recipient_account_id:
            return "CONFLICT"

        # Check existence in both tables
        is_merchant = conn.execute("SELECT 1 FROM merchants WHERE id = ?", (merchant_id,)).fetchone() is not None
        is_account = conn.execute("SELECT 1 FROM accounts WHERE id = ?", (merchant_id,)).fetchone() is not None

        if is_merchant and is_account:
            return "COLLISION"
        if is_merchant:
            return "MERCHANT_ONLY"
        if is_account:
            return "ACCOUNT_ONLY"

        return "UNKNOWN"

    def audit(self):
        """Scan database and report totals and specific IDs for collisions/conflicts."""
        conn = self._get_connection()
        try:
            self.validate_schema(conn)
            records = conn.execute("SELECT id, merchant_id, recipient_account_id FROM transactions").fetchall()

            stats = {
                "MERCHANT_ONLY": 0,
                "ACCOUNT_ONLY": 0,
                "COLLISION": [],
                "UNKNOWN": [],
                "CONFLICT": []
            }

            for rec in records:
                cls = self.classify_record(conn, rec)
                if cls in ["MERCHANT_ONLY", "ACCOUNT_ONLY"]:
                    stats[cls] += 1
                else:
                    stats[cls].append(rec['id'])

            print("--- Migration Audit Report ---")
            print(f"MERCHANT_ONLY: {stats['MERCHANT_ONLY']}")
            print(f"ACCOUNT_ONLY: {stats['ACCOUNT_ONLY']} (Eligible)")
            print(f"COLLISION: {len(stats['COLLISION'])} IDs: {stats['COLLISION']}")
            print(f"UNKNOWN: {len(stats['UNKNOWN'])} IDs: {stats['UNKNOWN']}")
            print(f"CONFLICT: {len(stats['CONFLICT'])} IDs: {stats['CONFLICT']}")

            is_safe = len(stats['COLLISION']) == 0 and len(stats['UNKNOWN']) == 0 and len(stats['CONFLICT']) == 0
            print(f"\nSafe to apply: {'YES' if is_safe else 'NO'}")
            return is_safe
        finally:
            conn.close()

    def apply(self):
        """Perform the migration atomically."""
        # 1. Backup
        backup_file = self.backup_database()
        print(f"Backup created: {backup_file}")

        conn = self._get_connection()
        try:
            self.validate_schema(conn)

            # Preliminary scan to ensure no refusals
            records = conn.execute("SELECT id, merchant_id, recipient_account_id FROM transactions").fetchall()
            for rec in records:
                cls = self.classify_record(conn, rec)
                if cls in ["COLLISION", "UNKNOWN", "CONFLICT"]:
                    raise MigrationError(f"Refusing migration: record {rec['id']} classified as {cls}")

            # 2. Atomic Transaction
            conn.execute("BEGIN TRANSACTION")

            for rec in records:
                # Re-validate immediately before update
                current_rec = conn.execute("SELECT merchant_id, recipient_account_id FROM transactions WHERE id = ?", (rec['id'],)).fetchone()
                cls = self.classify_record(conn, current_rec)

                if cls == "ACCOUNT_ONLY":
                    conn.execute(
                        "UPDATE transactions SET recipient_account_id = ?, merchant_id = NULL WHERE id = ?",
                        (current_rec['merchant_id'], rec['id'])
                    )
                elif cls != "MERCHANT_ONLY": # Merchant only is fine to leave alone, but others are errors
                    # Note: record might have changed since preliminary scan
                    raise MigrationError(f"Invariant violation during update: record {rec['id']} is now {cls}")

            # 3. Invariants Verification
            # (1) No overlap of recipient fields: In this context, we just ensured we only set recipient_account_id when merchant_id was cleared.
            # (2) No orphans in recipient_account_id: All must exist in accounts table.
            orphans = conn.execute("""
                SELECT t.recipient_account_id
                FROM transactions t
                LEFT JOIN accounts a ON t.recipient_account_id = a.id
                WHERE t.recipient_account_id IS NOT NULL AND a.id IS NULL
            """).fetchall()
            if orphans:
                raise MigrationError(f"Invariant failure: Orphan recipient accounts found: {orphans}")

            # (3) No account IDs left in merchant_id
            remnants = conn.execute("""
                SELECT t.merchant_id
                FROM transactions t
                JOIN accounts a ON t.merchant_id = a.id
            """).fetchall()
            if remnants:
                raise MigrationError(f"Invariant failure: Account IDs still present in merchant_id: {remnants}")

            conn.commit()
            print("Migration applied successfully.")

        except Exception as e:
            conn.rollback()
            print(f"Migration failed. Transaction rolled back. Error: {e}")
            raise e
        finally:
            conn.close()

def main():
    parser = argparse.ArgumentParser(description="Database Migration Tool")
    parser.add_argument("db", help="Path to the SQLite database file")
    parser.add_argument("--apply", action="store_true", help="Apply the migration changes")
    args = parser.parse_args()

    tool = MigrationTool(args.db)
    if args.apply:
        try:
            tool.apply()
        except Exception:
            sys.exit(1)
    else:
        tool.audit()

if __name__ == "__main__":
    main()
