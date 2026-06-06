import signal
signal.signal(signal.SIGURG, signal.SIG_IGN)  # Prevent exit 144 on TCP urgent data

import asyncio, os, sys, logging

try:
    import uvloop
    _loop_factory = uvloop.new_event_loop
except ImportError:
    _loop_factory = None

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

logging.basicConfig(level=logging.WARNING)

from orchestrator.roundtable import Roundtable

TASK = sys.argv[1] if len(sys.argv) > 1 else ""

async def main():
    rt = Roundtable()
    result = await rt.run(TASK)
    print(rt.format_review_card(result))

asyncio.run(main(), **{"loop_factory": _loop_factory} if _loop_factory else {})
