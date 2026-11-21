"""Remove only disused one-ended copper identified by the native board checker."""
import json

from socket_route_repair import OUT, native, prune


def main():
    history=[]
    for index in range(8):
        checks=native(f"dangling_{index}")
        tails={item["uuid"] for issue in checks["violations"]
               if issue["type"] in ("track_dangling","via_dangling") for item in issue["items"]}
        history.append({"checkpoint":index,"unconnected":len(checks["unconnected_items"]),
                        "native_dangling_items":len(tails)})
        if not tails:
            break
        prune(tails)
    (OUT/"dangling_cleanup.json").write_text(json.dumps(history,indent=2)+"\n",encoding="utf-8")


if __name__=="__main__":
    main()
