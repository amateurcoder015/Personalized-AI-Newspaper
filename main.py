import argparse
import logging
import sys
from pathlib import Path
from app.config import load_config
from app.pipeline import NewspaperPipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("main")


def parse_args():
    parser = argparse.ArgumentParser(description="Personal AI Daily Executive Newspaper Generator")
    parser.add_argument("--dry-run", action="store_true", help="Run complete 12-section pipeline locally without sending delivery")
    parser.add_argument("--weekly", action="store_true", help="Include weekly features (GitHub finds & weekly analysis)")
    parser.add_argument("--collect", action="store_true", help="Only collect RSS news and store in SQLite")
    parser.add_argument("--send", action="store_true", help="Send the most recent generated edition via email/WhatsApp")
    parser.add_argument("--test-email", action="store_true", help="Test SMTP email credentials")
    parser.add_argument("--test-llm", action="store_true", help="Test LLM provider connection")
    return parser.parse_args()


def main():
    args = parse_args()
    config = load_config()
    pipeline = NewspaperPipeline(config=config)

    if args.test_email:
        logger.info("Testing Email Configuration...")
        success = pipeline.email_delivery.test_connection()
        if success:
            logger.info("✓ Email test SUCCESSFUL!")
        else:
            logger.error("✗ Email test FAILED. Please check .env credentials.")
        return

    if args.test_llm:
        logger.info("Testing LLM Provider Connection...")
        res = pipeline.llm_provider.generate("Say 'Hello Executive Daily Brief!'")
        logger.info(f"LLM Response: {res}")
        return

    if args.collect:
        logger.info("Running News Collection Only...")
        pipeline.rss_collector.collect()
        return

    if args.send:
        logger.info("Sending Most Recent Edition...")
        editions = pipeline.db.get_editions(limit=1)
        if not editions:
            logger.error("No generated edition found in database.")
            return
        latest = editions[0]
        html_path = Path(latest.html_path)
        if not html_path.exists():
            logger.error(f"Edition file not found at {html_path}")
            return
        with open(html_path, "r", encoding="utf-8") as f:
            html_content = f.read()

        pipeline.email_delivery.send_newspaper(html_content, pdf_path=latest.pdf_path)
        return

    # Default / dry-run pipeline execution
    dry_run_mode = args.dry_run or not (config.email_enabled or config.whatsapp_enabled)
    result = pipeline.run_pipeline(dry_run=dry_run_mode, include_github=True)

    usage = result.get("usage_summary", {})
    print("\n" + "=" * 60)
    print("NEWSPAPER GENERATED SUCCESSFULLY")
    print("=" * 60)
    print(f"Edition ID     : {result['edition_id']}")
    print(f"Stories Count  : {result['stories_count']}")
    print(f"HTML Path      : {result['html_path']}")
    print(f"PDF Path       : {result['pdf_path']}")
    if dry_run_mode:
        print("Delivery Mode  : DRY RUN (Local generation)")
    else:
        print(f"Email Sent     : {result['email_sent']}")
    print("-" * 60)
    print("LLM TOKEN & COST ACCOUNTING")
    print(f"Calls          : {usage.get('calls', 0)}")
    print(f"Input Tokens   : {usage.get('input_tokens', 0)}")
    print(f"Output Tokens  : {usage.get('output_tokens', 0)}")
    print(f"Cache Hits     : {usage.get('cache_hits', 0)}")
    print(f"Est. Cost      : {usage.get('estimated_cost', '$0.00')}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
