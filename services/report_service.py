from services.market_engine import market_engine
from services.report_generator import report_generator
from utils.logger import get_logger

logger = get_logger(__name__)


class ReportService:
    """High-level report builder used by market handlers."""

    async def build_standard_report(self, symbol: str) -> str:
        analysis = await market_engine.analyze_symbol(symbol)
        return await report_generator.generate_market_report(analysis)

    async def build_signal_report(self, symbol: str) -> str:
        analysis = await market_engine.analyze_symbol(symbol)
        return report_generator.generate_signal_report(analysis)

    async def build_executive_summary(self, symbol: str) -> str:
        analysis = await market_engine.analyze_symbol(symbol)
        return await report_generator.generate_summary_report(analysis)

    async def build_document_report(self, symbol: str) -> str:
        analysis = await market_engine.analyze_symbol(symbol)
        return await report_generator.generate_document_report(analysis)

    async def build_scan_report(self, symbols: list[str] | None = None) -> str:
        analyses = await market_engine.scan_market(symbols=symbols)
        return report_generator.generate_scan_report(analyses)


report_service = ReportService()
