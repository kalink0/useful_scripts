import argparse
from pathlib import Path
from bubbly.exporter import BubblyExporter
from bubbly.parsers.whatsapp_chat_export import WhatsAppChatExportParser
from bubbly.utils import prepare_input_generic  # handles zip/folder/file

# ----------------------
# Parser registry
# ----------------------
PARSERS = {
    "whatsapp_export": WhatsAppChatExportParser,
    # Add future parsers here
}

# ----------------------
# CLI
# ----------------------
def parse_args():
    parser = argparse.ArgumentParser(description="Bubbly Launcher - Chat Export Viewer")
    parser.add_argument("--source", required=True, help=f"Parser name. Available: {list(PARSERS.keys())}")
    parser.add_argument("--input", required=True, help="Input file/folder/zip")
    parser.add_argument("--output", required=True, help="Output folder for HTML report")
    parser.add_argument("--user", required=True, help="User generating the report")
    parser.add_argument("--case", required=True, help="Case number")
    parser.add_argument("--chat_name", default="Chat Export", help="Chat/Contact name")
    parser.add_argument("--templates_folder", required=True, help="Path to templates folder")
    parser.add_argument("--extra_args", nargs="*", help="Parser-specific args as key=value pairs")
    return parser.parse_args()

# ----------------------
# Parse key=value pairs
# ----------------------
def parse_extra_args(extra_args_list):
    kwargs = {}
    if extra_args_list:
        for item in extra_args_list:
            if "=" in item:
                k, v = item.split("=", 1)
                # Convert true/false to bool
                if v.lower() == "true":
                    v = True
                elif v.lower() == "false":
                    v = False
                kwargs[k] = v
    return kwargs

# ----------------------
# Main
# ----------------------
def main():
    args = parse_args()
    parser_class = PARSERS.get(args.source)
    if not parser_class:
        raise ValueError(f"Unknown parser {args.source}. Available: {list(PARSERS.keys())}")

    # Prepare input (zip/folder/file)
    input_path, media_folder = prepare_input_generic(args.input)

    # Parser-specific kwargs
    extra_kwargs = parse_extra_args(args.extra_args)

    # Add generic metadata
    extra_kwargs.update({
        "user": args.user,
        "case": args.case,
        "chat_name": args.chat_name,
    })

    # Initialize parser
    parser_instance = parser_class()

    # Parse messages
    messages, metadata = parser_instance.parse(input_path, media_folder, **extra_kwargs)

    # Export HTML
    exporter = BubblyExporter(messages, media_folder, args.output, metadata, templates_folder=args.templates_folder)
    exporter.export_html()

if __name__ == "__main__":
    main()
