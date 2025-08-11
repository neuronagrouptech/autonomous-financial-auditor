"""Parser factory for selecting appropriate parser based on file type."""

import logging
from typing import List, Optional

from autonomous_financial_auditor.models import FinancialDocument
from autonomous_financial_auditor.parsers.base import BaseParser
from autonomous_financial_auditor.parsers.csv_parser import CSVParser
from autonomous_financial_auditor.parsers.markdown_parser import MarkdownParser

logger = logging.getLogger(__name__)


class ParserFactory:
    """Factory class for selecting appropriate parser based on file type."""
    
    def __init__(self) -> None:
        """Initialize the parser factory with available parsers."""
        self.parsers: List[BaseParser] = [
            CSVParser(),
            MarkdownParser(),
        ]
        self.logger = logger
    
    def get_parser(self, file_path: str) -> Optional[BaseParser]:
        """Get the appropriate parser for the given file."""
        for parser in self.parsers:
            if parser.can_parse(file_path):
                self.logger.debug(f"Selected {parser.__class__.__name__} for {file_path}")
                return parser
        
        self.logger.warning(f"No parser found for file: {file_path}")
        return None
    
    def parse_file(self, file_path: str, content: str) -> Optional[FinancialDocument]:
        """Parse a file using the appropriate parser."""
        parser = self.get_parser(file_path)
        if not parser:
            return None
        
        try:
            return parser.parse(file_path, content)
        except Exception as e:
            self.logger.error(f"Error parsing {file_path} with {parser.__class__.__name__}: {e}")
            return None
    
    def get_supported_extensions(self) -> List[str]:
        """Get list of supported file extensions."""
        extensions = []
        
        # Common extensions for each parser type
        extension_map = {
            CSVParser: ['.csv', '.tsv'],
            MarkdownParser: ['.md', '.markdown'],
        }
        
        for parser in self.parsers:
            parser_type = type(parser)
            if parser_type in extension_map:
                extensions.extend(extension_map[parser_type])
        
        return sorted(list(set(extensions)))
    
    def add_parser(self, parser: BaseParser) -> None:
        """Add a custom parser to the factory."""
        self.parsers.append(parser)
        self.logger.info(f"Added custom parser: {parser.__class__.__name__}")
    
    def remove_parser(self, parser_class: type) -> bool:
        """Remove a parser from the factory by class type."""
        original_count = len(self.parsers)
        self.parsers = [p for p in self.parsers if not isinstance(p, parser_class)]
        removed_count = original_count - len(self.parsers)
        
        if removed_count > 0:
            self.logger.info(f"Removed {removed_count} parser(s) of type {parser_class.__name__}")
            return True
        
        return False


# Global parser factory instance
parser_factory = ParserFactory()