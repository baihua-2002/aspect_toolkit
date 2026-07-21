import sys

from connector import AspectConnector, ConnectorError


def main():
    connector = AspectConnector()
    try:
        connector.validate()
        print(f"ASPECT binary OK: {connector.config.aspect_binary}")
    except ConnectorError as e:
        print(f"Configuration error: {e}")
        return

    if len(sys.argv) > 1:
        result = connector.run(sys.argv[1])
        print(f"Success: {result.success}, elapsed: {result.elapsed_seconds:.1f}s")
        if result.output_directory:
            print(f"Output: {result.output_directory}")
        if not result.success:
            print(result.stderr[-500:])


if __name__ == "__main__":
    main()
