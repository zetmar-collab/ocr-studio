import sys

if "--selftest" in sys.argv:
    # Test dymny bez okna: sprawdza silnik, jezyki i slowniki (patrz src/selftest.py).
    from src.selftest import main as selftest_main

    raise SystemExit(selftest_main(sys.argv))

from src.main import run  # noqa: E402

if __name__ == "__main__":
    run()
