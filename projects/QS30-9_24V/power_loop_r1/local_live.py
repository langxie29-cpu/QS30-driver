"""Use installed Harness in a private home, reuse existing bounded coordinator."""
import os, sys
import local_probe
os.environ.update(local_probe.setup())
import orchestrate
if __name__ == '__main__':
    orchestrate.main()
