"""Logstash DSL parser using pyparsing."""

from pathlib import Path
from typing import Any

import pyparsing as pp
from pyparsing import (
    CaselessKeyword,
    Group,
    Keyword,
    OneOrMore,
    Optional,
    QuotedString,
    StringEnd,
    StringStart,
    Suppress,
    Word,
    ZeroOrMore,
    alphanums,
    alphas,
    line,
    lineno,
    nums,
    pythonStyleComment,
)

from lv_py.models import PluginType
from lv_py.models.logstash_config import LogstashConfiguration, LogstashPlugin

# Enable packrat parsing for better performance
pp.ParserElement.enablePackrat()


def _create_logstash_grammar() -> pp.ParserElement:
    """Create pyparsing grammar for Logstash DSL."""
    # Basic elements
    LBRACE = Suppress("{")
    RBRACE = Suppress("}")
    LBRACK = Suppress("[")
    RBRACK = Suppress("]")
    EQUALS = Suppress("=>")
    COMMA = Suppress(",")

    # Identifiers and values
    identifier = Word(alphas, alphanums + "_")
    integer = Word(nums).setParseAction(lambda t: int(t[0]))
    boolean = (Keyword("true") | Keyword("false")).setParseAction(lambda t: t[0] == "true")

    # String literals (single or double quoted)
    string_literal = (
        QuotedString('"', escChar="\\") | QuotedString("'", escChar="\\")
    ).setParseAction(lambda t: t[0])

    # Array values
    array = Group(LBRACK + Optional(string_literal + ZeroOrMore(COMMA + string_literal)) + RBRACK)

    # Configuration value (can be string, int, boolean, or array)
    config_value = array | string_literal | integer | boolean

    # Config key-value pair: key => value
    config_pair = Group(identifier + EQUALS + config_value)

    # Plugin configuration: { key => value, ... }
    plugin_config = LBRACE + ZeroOrMore(config_pair) + RBRACE

    # Plugin: plugin_name { config }
    plugin = Group(
        identifier("plugin_name") + Optional(plugin_config)("config")
    ).setParseAction(_attach_line_number)

    # Block type markers (use Literal instead of CaselessKeyword for better control)
    input_marker = pp.Literal("input") | pp.Literal("INPUT")
    filter_marker = pp.Literal("filter") | pp.Literal("FILTER")
    output_marker = pp.Literal("output") | pp.Literal("OUTPUT")

    # Define blocks with explicit type marking
    input_block = Group(
        input_marker.setResultsName("block_type") + LBRACE + ZeroOrMore(plugin) + RBRACE
    )
    filter_block = Group(
        filter_marker.setResultsName("block_type") + LBRACE + ZeroOrMore(plugin) + RBRACE
    )
    output_block = Group(
        output_marker.setResultsName("block_type") + LBRACE + ZeroOrMore(plugin) + RBRACE
    )

    # Complete Logstash configuration - use OneOrMore to ensure at least one block
    config_block = input_block | filter_block | output_block
    logstash_config = OneOrMore(config_block)

    # Ignore comments
    logstash_config.ignore(pythonStyleComment)
    logstash_config.ignore(pp.cStyleComment)

    return logstash_config


def _attach_line_number(s: str, loc: int, toks: pp.ParseResults) -> pp.ParseResults:
    """Attach line number to parsed plugin."""
    toks["line_number"] = lineno(loc, s)
    return toks


def _parse_plugin(plugin_data: pp.ParseResults, plugin_type: PluginType) -> LogstashPlugin:
    """Convert parsed plugin data to LogstashPlugin model."""
    config_dict: dict[str, Any] = {}

    if "config" in plugin_data and plugin_data["config"]:
        for key_value in plugin_data["config"]:
            if len(key_value) >= 2:
                key, value = key_value[0], key_value[1]
                # Handle arrays
                if isinstance(value, pp.ParseResults) and not isinstance(value, str):
                    config_dict[key] = list(value)
                else:
                    config_dict[key] = value

    return LogstashPlugin(
        plugin_type=plugin_type,
        plugin_name=str(plugin_data["plugin_name"]),
        config=config_dict,
        line_number=plugin_data.get("line_number", 1),
        conditionals=None,  # TODO: Add support for if/else conditionals
    )


def parse_file(file_path: Path) -> LogstashConfiguration:
    """
    Parse a Logstash configuration file and return LogstashConfiguration.

    Args:
        file_path: Path to the .conf file

    Returns:
        LogstashConfiguration with parsed inputs, filters, outputs

    Raises:
        ValueError: If parsing fails or file is invalid
    """
    # Use regex-based parser for reliability
    # pyparsing has issues with multi-block parsing in this case
    from lv_py.parser.logstash_parser_regex import parse_file_regex

    return parse_file_regex(file_path)
