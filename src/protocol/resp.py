"""
Redis Serialization Protocol (RESP2) Parser & Serializer.
Jerry A. Nabasu (@JayNabasu)
"""

from typing import Any, Tuple, List, Optional

class RESPParser:
    @staticmethod
    def serialize(data: Any) -> bytes:
        """Serializes a Python object into RESP bytes."""
        if data is None:
            return b"$-1\r\n"
        elif isinstance(data, str):
            payload = data.encode("utf-8")
            return f"${len(payload)}\r\n".encode("utf-8") + payload + b"\r\n"
        elif isinstance(data, int):
            return f":{data}\r\n".encode("utf-8")
        elif isinstance(data, float):
            payload = str(data).encode("utf-8")
            return f"${len(payload)}\r\n".encode("utf-8") + payload + b"\r\n"
        elif isinstance(data, bool):
            return b":1\r\n" if data else b":0\r\n"
        elif isinstance(data, Exception):
            return f"-ERR {str(data)}\r\n".encode("utf-8")
        elif isinstance(data, (list, tuple)):
            parts = [f"*{len(data)}\r\n".encode("utf-8")]
            for item in data:
                parts.append(RESPParser.serialize(item))
            return b"".join(parts)
        elif isinstance(data, dict):
            # Flatten dict into array of key, value, key, value
            flattened = []
            for k, v in data.items():
                flattened.append(k)
                flattened.append(v)
            return RESPParser.serialize(flattened)
        else:
            return RESPParser.serialize(str(data))

    @staticmethod
    def parse_command(raw_data: bytes) -> Tuple[Optional[List[str]], bytes]:
        """Parses a raw incoming RESP buffer and returns (command_args, remaining_bytes)."""
        if not raw_data:
            return None, b""

        # Check if line-based inline command (e.g. "PING\r\n" or "SET foo bar\r\n")
        if not raw_data.startswith(b"*"):
            if b"\r\n" in raw_data:
                line, rest = raw_data.split(b"\r\n", 1)
                parts = [p.decode("utf-8") for p in line.strip().split() if p]
                return parts, rest
            return None, raw_data

        # Standard RESP Array parser
        lines = raw_data.split(b"\r\n")
        if len(lines) < 2:
            return None, raw_data

        first_line = lines[0]
        if not first_line.startswith(b"*"):
            return None, raw_data

        try:
            num_elements = int(first_line[1:])
        except ValueError:
            return None, raw_data

        args = []
        line_idx = 1
        for _ in range(num_elements):
            if line_idx >= len(lines):
                return None, raw_data # Incomplete buffer
            type_line = lines[line_idx]
            if type_line.startswith(b"$"):
                length = int(type_line[1:])
                if length == -1:
                    args.append(None)
                    line_idx += 1
                else:
                    line_idx += 1
                    if line_idx >= len(lines):
                        return None, raw_data
                    args.append(lines[line_idx].decode("utf-8"))
                    line_idx += 1
            else:
                line_idx += 1

        # Reconstruct remaining bytes
        consumed_length = len(b"\r\n".join(lines[:line_idx]) + b"\r\n")
        remaining = raw_data[consumed_length:]
        return args, remaining
