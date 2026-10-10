#!/usr/bin/env python3
"""Chrome transport test. Takes the primary session; close other tabs first."""
import base64
import json
from pathlib import Path
import subprocess
import tempfile
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
URL = "https://retroarch.apps.sno.batchelor.live"

SDL_PROBE = r'''
import ctypes as c, json, time
s=c.CDLL("libSDL2-2.0.so.0")
s.SDL_Init(0x2000)
s.SDL_GameControllerOpen.restype=c.c_void_p
s.SDL_GameControllerGetButton.argtypes=[c.c_void_p,c.c_int]
s.SDL_GameControllerGetAxis.argtypes=[c.c_void_p,c.c_int]
s.SDL_GameControllerGetAxis.restype=c.c_int16
s.SDL_GameControllerName.argtypes=[c.c_void_p]
s.SDL_GameControllerName.restype=c.c_char_p
count=s.SDL_NumJoysticks()
p=s.SDL_GameControllerOpen(0)
if not p: raise RuntimeError("No virtual controller")
name=s.SDL_GameControllerName(p).decode()
seen=set()
end=time.monotonic()+12
while time.monotonic()<end:
    s.SDL_GameControllerUpdate()
    seen.add((s.SDL_GameControllerGetButton(p,0),s.SDL_GameControllerGetAxis(p,0),s.SDL_GameControllerGetAxis(p,4),s.SDL_GameControllerGetButton(p,11)))
    time.sleep(.01)
print(json.dumps({"name":name,"count":count,"states":sorted(seen)}))
'''


def synthetic_controller(page):
    page.evaluate("""() => {
      window.testPad = {id:'Xbox Series synthetic acceptance probe',index:0,connected:true,
        mapping:'standard',timestamp:performance.now(),axes:[0,0,0,0],
        buttons:Array.from({length:17},()=>({pressed:false,touched:false,value:0}))};
      Object.defineProperty(navigator,'getGamepads',{value:()=>[window.testPad,null,null,null],configurable:true});
      const event=new Event('gamepadconnected');
      Object.defineProperty(event,'gamepad',{value:window.testPad}); window.dispatchEvent(event);
    }""")
    # Give the browser a real changed input to select this pad's slot.
    page.evaluate("testPad.buttons[0]={pressed:true,touched:true,value:1}; testPad.timestamp=performance.now()")
    page.wait_for_timeout(1000)
    page.evaluate("testPad.buttons[0]={pressed:false,touched:false,value:0}; testPad.timestamp=performance.now()")
    with tempfile.TemporaryFile(mode="w+") as output:
        process = subprocess.Popen(["oc", "-n", "retroarch", "exec", "deployment/retroarch", "--",
            "bash", "-c", 'source "${XDG_RUNTIME_DIR}/container-env"; exec python3 -c "$1"',
            "controller-probe", SDL_PROBE], stdout=output, stderr=subprocess.PIPE, text=True)
        page.wait_for_timeout(2000)
        for expression in [
            "testPad.buttons[0]={pressed:true,touched:true,value:1}",
            "testPad.buttons[0]={pressed:false,touched:false,value:0}",
            "testPad.axes[0]=0.75; testPad.buttons[6]={pressed:true,touched:true,value:0.8}",
            "testPad.axes[0]=0; testPad.buttons[6]={pressed:false,touched:false,value:0}",
            "testPad.buttons[12]={pressed:true,touched:true,value:1}",
            "testPad.buttons[12]={pressed:false,touched:false,value:0}"]:
            page.evaluate(expression + "; testPad.timestamp=performance.now()")
            page.wait_for_timeout(700)
        _, error = process.communicate(timeout=20)
        output.seek(0)
        raw = output.read()
    if process.returncode:
        return {"passed":False,"error":error[:500]}
    result = json.loads(raw)
    states = result["states"]
    result["passed"] = (any(s[0] == 1 for s in states) and any(s[1] > 10000 for s in states)
                        and any(s[2] > 10000 for s in states) and any(s[3] != 0 for s in states)
                        and any(s[0] == 0 and s[1] == 0 and s[2] == 0 and s[3] == 0 for s in states))
    result["note"] = "Synthetic browser input to server SDL2; does not validate physical Bluetooth controller"
    return result


def main():
    secret = json.loads(subprocess.check_output(
        ["oc", "-n", "retroarch", "get", "secret", "retroarch-login", "-o", "json"]))["data"]
    credentials = {key: base64.b64decode(secret[key]).decode() for key in ("username", "password")}
    output = ROOT / "recovery"
    output.mkdir(exist_ok=True)
    with sync_playwright() as p:
        anonymous = p.request.new_context()
        anonymous_status = anonymous.get(URL).status
        assert anonymous_status == 401, f"Unauthenticated response: {anonymous_status}"
        browser = p.chromium.launch(channel="chrome", headless=True,
            args=["--autoplay-policy=no-user-gesture-required"])
        context = browser.new_context(http_credentials=credentials, viewport={"width": 1920, "height": 1080})
        # Browser assets must be self-hosted, including when the WAN is down.
        context.route("**/*", lambda route: route.continue_()
                      if route.request.url.startswith(URL + "/") else route.abort())
        page = context.new_page()
        sockets = []
        errors = []

        def track(ws):
            item = {"path": ws.url.split("?")[0], "received_frames": 0, "received_bytes": 0}
            sockets.append(item)
            def received(payload):
                item["received_frames"] += 1
                item["received_bytes"] += len(payload)
            ws.on("framereceived", received)

        page.on("websocket", track)
        page.on("pageerror", lambda e: errors.append(str(e)[:300]))
        response = page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        page.mouse.click(960, 540)
        page.wait_for_timeout(30000)
        page.screenshot(path=str(output / "browser-session.png"))
        result = {"anonymous_status": anonymous_status, "authenticated_status": response.status,
                  "secure_context": page.evaluate("window.isSecureContext"),
                  "gamepad_api": page.evaluate("typeof navigator.getGamepads === 'function'"),
                  "title": page.title(), "sockets": sockets, "page_errors": errors,
                  "visible_text": page.locator("body").inner_text()[:4000],
                  "media": page.evaluate("Array.from(document.querySelectorAll('video,canvas')).map(e=>({tag:e.tagName,width:e.width,height:e.height,videoWidth:e.videoWidth,videoHeight:e.videoHeight}))")}
        interrupted = "Connection Terminated" in result["visible_text"]
        result["interrupted_by_other_client"] = interrupted
        result["synthetic_controller"] = ({"passed": False, "note": "Another primary browser took over; input test skipped"}
                                             if interrupted else synthetic_controller(page))
        (output / "browser-smoke.json").write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result, indent=2))
        browser.close()
        assert not interrupted, "Another browser took over the session; close other Route tabs before running this test"
        assert response.status == 200
        assert any(s["received_bytes"] > 100000 for s in sockets), "No substantial stream received"
        assert result["synthetic_controller"]["passed"], "Synthetic controller forwarding failed"


if __name__ == "__main__":
    main()
