"""Deterministic miniPaint UI replay. No source, network bodies, or canvas reads."""
import base64
from contextlib import contextmanager
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import time

from playwright.sync_api import sync_playwright, expect
from .png import EVIDENCE, FIXTURES, within, fixture_path, png_info, compare_pngs

URL = "https://viliusle.github.io/miniPaint/"
COLLECTED_VERSION = "4.14.3"


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


class MiniPaintAdapter:
    """One synchronous Playwright owner per browser session; no parallel controllers."""
    def __init__(self, artifact_dir, *, headed=True, timeout_ms=8000):
        self.artifact_dir = within(artifact_dir, EVIDENCE)
        self.artifact_dir.mkdir(parents=True, exist_ok=True)
        self.headed, self.timeout_ms = headed, timeout_ms
        self.actions = []
        self.identity = None
        self.page = self.context = self.browser = self.pw = None
        self.setup = self.input_path = self.accepted_percentage = None
        self.phase = "uninitialized"

    def __enter__(self):
        self.pw = sync_playwright().start()
        try:
            self.browser = self.pw.chromium.launch(headless=not self.headed, timeout=30000)
        except Exception:
            self.pw.stop()
            raise
        return self

    def __exit__(self, *args):
        if self.browser:
            self.browser.close()
        if self.pw:
            self.pw.stop()

    @contextmanager
    def action(self, name, **details):
        start = time.monotonic()
        record = {"action": name, "started_at": utc_now(), "status": "in_progress", **details}
        self.actions.append(record)
        write_json(self.artifact_dir / "actions.json", self.actions)
        try:
            yield record
            record["status"] = "passed"
        except Exception as error:
            record["status"] = "failed"
            record["error"] = {"type": type(error).__name__, "message": str(error)[:2000]}
            self.diagnostics(name)
            raise
        finally:
            record["finished_at"] = utc_now()
            record["elapsed_seconds"] = round(time.monotonic() - start, 3)
            write_json(self.artifact_dir / "actions.json", self.actions)

    def new_page(self):
        if self.context:
            self.context.close()
        self.context = self.browser.new_context(viewport={"width":1440,"height":1000},
            device_scale_factor=1, locale="en-US", timezone_id="America/Los_Angeles",
            accept_downloads=True, service_workers="block")
        self.page = self.context.new_page()
        self.page.set_default_timeout(self.timeout_ms)
        self.page.set_default_navigation_timeout(30000)
        # No tracing, HAR, console dumps, response listeners, or JS application state.
        self.page.goto(URL, wait_until="domcontentloaded")
        expect(self.page.get_by_role("menuitem", name="File", exact=True)).to_be_visible()

    def menu(self, *names):
        for name in names:
            self.page.get_by_role("menuitem", name=name, exact=True).click()

    def dialog(self, heading):
        dialog = self.page.get_by_role("dialog")
        expect(dialog).to_be_visible()
        expect(dialog.get_by_role("heading", name=heading, exact=True)).to_be_visible()
        return dialog

    def target_identity(self):
        self.menu("Help", "About ...")
        dialog = self.dialog("About")
        row = dialog.get_by_role("row", name=re.compile(r"^Version:"))
        version = row.get_by_role("cell").inner_text().strip()
        identity = {"name":"miniPaint", "url":self.page.url, "visible_about_version":version,
            "collected_version":COLLECTED_VERSION, "version_discrepancy":version != COLLECTED_VERSION,
            "build":"unknown; hosted URL is unpinned", "observed_at":utc_now(),
            "chromium_version":self.browser.version, "headed":self.headed,
            "viewport":{"width":1440,"height":1000}, "device_scale_factor":1}
        self.capture_screenshot(self.artifact_dir / "about.png")
        write_json(self.artifact_dir / "target.json", identity)
        dialog.get_by_role("button", name="Ok", exact=True).click()
        expect(dialog).not_to_be_visible()
        self.identity = identity
        return identity

    def capture_screenshot(self, output_path):
        output_path = within(output_path, self.artifact_dir)
        self.page.screenshot(path=str(output_path), full_page=False, timeout=self.timeout_ms)
        return str(output_path)

    def read_visible_dom(self, output_path):
        """Bounded visible DOM/accessibility only, never HTML/script or canvas data."""
        output_path = within(output_path, self.artifact_dir)
        aria = self.page.locator("body").aria_snapshot(timeout=self.timeout_ms)
        # DOM-backed properties of displayed controls only; no arbitrary JS supplied.
        controls = self.page.locator("body").evaluate("""body => {
            const all = [...body.querySelectorAll('button,input,select,textarea,label,h1,h2,a,[role="menuitem"]')];
            const visible = all.filter(e => e.getClientRects().length && getComputedStyle(e).visibility !== 'hidden');
            return visible.slice(0,250).map(e => ({tag:e.tagName,id:e.id,role:e.getAttribute('role'),
                label:e.getAttribute('aria-label'),title:e.getAttribute('title'),
                type:e.getAttribute('type'),text:(e.innerText || '').slice(0,200),
                value:('value' in e ? String(e.value).slice(0,200) : null),
                bounds:(()=>{const r=e.getBoundingClientRect();return {x:r.x,y:r.y,width:r.width,height:r.height}})()}));
        }""", timeout=self.timeout_ms)
        data = {"captured_at":utc_now(), "url":self.page.url,
                "accessibility":aria[:48000], "accessibility_truncated":len(aria)>48000,
                "visible_controls":controls, "control_limit":250}
        write_json(output_path, data)
        return data

    def capture_initial_interface(self):
        with self.action("initial_layout"):
            self.new_page()
            self.capture_screenshot(self.artifact_dir / "initial-interface.png")
            self.read_visible_dom(self.artifact_dir / "initial-visible-dom.json")
            return self.target_identity()

    def diagnostics(self, name):
        if not self.page:
            return
        safe = re.sub(r"[^a-zA-Z0-9_-]", "-", name)
        for capture, path in [(self.capture_screenshot, self.artifact_dir / f"failure-{safe}.png"),
                              (self.read_visible_dom, self.artifact_dir / f"failure-{safe}-dom.json")]:
            try:
                capture(path)
            except Exception:
                pass

    def assert_dimensions(self):
        w,h = self.setup["canvas_width"],self.setup["canvas_height"]
        expect(self.page.locator("body")).to_contain_text(re.compile(rf"Size:\s*{w}\s*x\s*{h}\s*px"), use_inner_text=True, timeout=self.timeout_ms)
        expect(self.page.locator("body")).to_contain_text(re.compile(r"Resolution:\s*72"), use_inner_text=True, timeout=self.timeout_ms)

    def reset_reference(self, document_setup):
        with self.action("reset_reference", setup=document_setup):
            required = {"transparent":True,"resolution_ui":72,"imported_layer_offset":[0,0],
                        "layer_opacity_percent":100,"layer_rotation_degrees":0,
                        "fresh_original_input":True,"other_visible_layers":False}
            if any(document_setup.get(k) != v for k,v in required.items()):
                raise ValueError("Unsupported document setup; must match the collected transparent single-layer setup")
            for key in ("canvas_width","canvas_height"):
                if type(document_setup.get(key)) is not int or not 1 <= document_setup[key] <= 2048:
                    raise ValueError("Document dimensions must be integers in 1..2048")
            self.setup = dict(document_setup)
            self.input_path = self.accepted_percentage = None
            self.new_page()  # New browser context discards previous layers, settings, undo and dialogs.
            self.target_identity()
            self.menu("File", "New")
            dialog = self.dialog("New file")
            for label,key in (("Width:","canvas_width"),("Height:","canvas_height")):
                field = dialog.get_by_role("row", name=re.compile("^"+re.escape(label))).get_by_role("spinbutton")
                field.fill(str(document_setup[key]))
                expect(field).to_have_value(str(document_setup[key]))
            transparent = dialog.get_by_role("checkbox", name="Toggle", exact=True)
            transparent.check()
            expect(transparent).to_be_checked()
            self.capture_screenshot(self.artifact_dir / "new-document-settings.png")
            dialog.get_by_role("button", name="Ok", exact=True).click()
            expect(dialog).not_to_be_visible()
            self.page.get_by_role("button", name="Fit", exact=True).click()
            self.capture_screenshot(self.artifact_dir / "fresh-document.png")
            self.assert_dimensions()
            self.phase = "reset"

    def verify_import(self, path, *, data_url=False):
        # Visible DOM field IDs discovered in this session, where labels lack associations.
        expect(self.page.locator("#detail_width")).to_have_value(str(self.setup["canvas_width"]))
        expect(self.page.locator("#detail_height")).to_have_value(str(self.setup["canvas_height"]))
        for field,value in (("x",0),("y",0),("rotate",0),("opacity",100)):
            expect(self.page.locator(f"#detail_{field}")).to_have_value(str(value))
        expect(self.page.locator('[id="layer_name"]')).to_have_count(1)
        if not data_url:
            expect(self.page.get_by_role("button",name=path.name,exact=True)).to_be_visible()
        self.assert_dimensions()
        expect(self.page.get_by_text("Blur", exact=True)).not_to_be_visible()
        self.capture_screenshot(self.artifact_dir / "imported-original.png")

    def import_image(self, input_path, *, route="auto"):
        if self.phase != "reset":
            raise ValueError("Import requires a fresh reset document")
        path = within(input_path, FIXTURES / "inputs")
        info = png_info(path)
        if (info["width"],info["height"]) != (self.setup["canvas_width"],self.setup["canvas_height"]):
            raise ValueError("Input dimensions do not match fresh document")
        if path.stat().st_size > 8*1024*1024:
            raise ValueError("Input exceeds bounded import size")
        routes = ["file_chooser","data_url"] if route == "auto" else [route]
        if any(r not in ("file_chooser","data_url") for r in routes):
            raise ValueError("Unknown import route")
        failures=[]
        for index,method in enumerate(routes):
            try:
                if index:
                    self.reset_reference(self.setup)
                with self.action("import_image", route=method, input_path=str(path), input=info):
                    self.menu("File","Open >")
                    if method == "file_chooser":
                        with self.page.expect_file_chooser(timeout=5000) as chooser:
                            self.page.get_by_role("menuitem",name="Open File ... Shortcut Key: O",exact=True).click()
                        chooser.value.set_files(str(path), timeout=self.timeout_ms)
                    else:
                        self.menu("Open Data URL ...")
                        dialog=self.dialog("Open data URL")
                        dialog.get_by_role("textbox").fill("data:image/png;base64,"+base64.b64encode(path.read_bytes()).decode("ascii"))
                        dialog.get_by_role("button",name="Ok",exact=True).click()
                        expect(dialog).not_to_be_visible()
                    self.verify_import(path, data_url=method=="data_url")
                    self.input_path = path
                    self.phase = "imported"
                    return {"route":method, "input":info, "earlier_failures":failures}
            except Exception as error:
                failures.append({"route":method,"type":type(error).__name__,"message":str(error)[:1000]})
        raise RuntimeError(f"Both permitted import routes exhausted: {failures}")

    def apply_operation(self, parameters):
        if self.phase != "imported":
            raise ValueError("Operation requires an original imported image")
        if set(parameters) != {"Percentage"} or type(parameters["Percentage"]) is not int or not 0 <= parameters["Percentage"] <= 50:
            raise ValueError("Percentage must be an integer in the observed UI range 0..50")
        value = parameters["Percentage"]
        with self.action("apply_operation", operation="Gaussian Blur", requested=parameters) as action:
            self.menu("Effects","Common Filters >","Gaussian Blur ...")
            dialog = self.dialog("Blur")
            slider = dialog.get_by_role("row",name=re.compile(r"^Percentage:")).get_by_role("slider")
            for attr,expected in (("min","0"),("max","50"),("step","1")):
                expect(slider).to_have_attribute(attr,expected)
            slider.press("Home")
            for _ in range(value):
                slider.press("ArrowRight")
            expect(slider).to_have_value(str(value))
            expect(dialog.get_by_role("row",name=re.compile(r"^Percentage:")).get_by_role("cell").last).to_have_text(str(value))
            self.accepted_percentage=value
            action["accepted_percentage"]=value
            self.capture_screenshot(self.artifact_dir / "accepted-percentage.png")
            dialog.get_by_role("button",name="Ok",exact=True).click()
            expect(dialog).not_to_be_visible()
            expect(self.page.get_by_text("Blur", exact=True)).to_be_visible(timeout=self.timeout_ms)
            self.assert_dimensions()
            self.capture_screenshot(self.artifact_dir / "operation-complete.png")
            self.phase="operated"

    def export_png(self, output_path):
        if self.phase not in ("imported","operated"):
            raise ValueError("Export requires imported or operated content")
        path = within(output_path,self.artifact_dir)
        if path.exists():
            raise ValueError("Refusing to reuse or overwrite an export path")
        with self.action("export_png", output_path=str(path), phase=self.phase) as action:
            self.menu("File","Export ... Shortcut Key: S")
            dialog=self.dialog("Export")
            name = path.stem
            dialog.get_by_role("row",name=re.compile(r"^File name:")).get_by_role("textbox").fill(name)
            png=dialog.get_by_role("radio",name="PNG - Portable Network Graphics",exact=True)
            all_layers=dialog.get_by_role("radio",name="All",exact=True)
            png.check(); all_layers.check()
            expect(png).to_be_checked(); expect(all_layers).to_be_checked()
            expect(dialog.get_by_role("row",name=re.compile(r"^Resolution:")).get_by_role("cell")).to_have_text("72")
            expect(dialog.get_by_role("spinbutton")).to_have_count(0)  # Observed export UI has no resize controls.
            self.capture_screenshot(self.artifact_dir / (name+"-export-settings.png"))
            with self.page.expect_download(timeout=15000) as event:
                dialog.get_by_role("button",name="Ok",exact=True).click()
            download=event.value
            if download.suggested_filename != name+".png":
                raise ValueError("Fresh download filename does not match current experiment export")
            failure=download.failure()
            if failure:
                raise RuntimeError("Browser download failed: "+failure)
            download.save_as(str(path))
            expect(dialog).not_to_be_visible()
            info=png_info(path)
            if (info["width"],info["height"]) != (self.setup["canvas_width"],self.setup["canvas_height"]):
                raise ValueError("Export decoded dimensions mismatch")
            action.update({"download_observed_at":utc_now(),"suggested_filename":download.suggested_filename,
                           "format":"PNG","save_layers":"All","resizing":False,"output":info})
            return info

    def run_experiment(self, case, *, repeat=1, import_route="auto"):
        start=time.monotonic()
        report={"case_id":case["case_id"],"repeat":repeat,"started_at":utc_now(),
                "parameters":case["operation"]["parameters"],"status":"infrastructure_failure",
                "infrastructure_errors":[],"artifacts":str(self.artifact_dir)}
        try:
            input_path=fixture_path(case["input_path"])
            expected_path=fixture_path(case["output_path"])
            for path,key in ((input_path,"input"),(expected_path,"output")):
                info=png_info(path)
                if info["png_sha256"] != case["hashes"][key+"_png_sha256"] or info["rgba_sha256"] != case["hashes"][key+"_decoded_rgba_sha256"]:
                    raise ValueError("Fixture integrity mismatch; expected data must remain unchanged")
            if case["operation"]["name"] != "Gaussian Blur" or case["operation"]["dialog_title"] != "Blur":
                raise ValueError("Only the collected Gaussian Blur operation is supported")
            self.reset_reference(case["document_setup"])
            report["target"]=self.identity
            report["import"]=self.import_image(input_path,route=import_route)
            # Extra visible export proves original pixels were imported before applying blur.
            original_path=self.artifact_dir / "original-confirmation.png"
            report["original_export"]=self.export_png(original_path)
            report["original_confirmation"]=compare_pngs(original_path,input_path)
            if not report["original_confirmation"]["rgba_equal"]:
                raise ValueError("Original decoded input was not reproduced by the import/setup route")
            self.apply_operation(case["operation"]["parameters"])
            report["accepted_percentage"]=self.accepted_percentage
            output_path=self.artifact_dir / "output.png"
            report["output"]=self.export_png(output_path)
            report["output_path"]=str(output_path)
            report["reference_comparison"]=compare_pngs(output_path,expected_path)
            report["status"]="passed" if report["reference_comparison"]["rgba_equal"] else "reference_mismatch"
        except Exception as error:
            report["infrastructure_errors"].append({"type":type(error).__name__,"message":str(error)[:2000]})
            self.diagnostics("experiment")
        finally:
            report["target"]=self.identity
            report["actions"]=self.actions
            report["finished_at"]=utc_now()
            report["elapsed_seconds"]=round(time.monotonic()-start,3)
            write_json(self.artifact_dir / "report.json",report)
        return report
