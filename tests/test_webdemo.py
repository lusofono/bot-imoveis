"""The static demo (bot-mail webdemo): plain files, fictitious data, and every step answered without a server."""
import json
from pathlib import Path
import re
import subprocess
import zipfile
import pytest
from backend.webdemo import build

ROOT = Path(__file__).resolve().parent.parent
JSC = Path("/System/Library/Frameworks/JavaScriptCore.framework/Versions/Current/Helpers/jsc")
HERE = Path(__file__).resolve().parent / "webdemo"
# What the demo answers from the recordings (the page's read-only calls) and what it says needs the full version.
RECORDED = {"api/contacts/ignored", "api/todo", "api/visits/analysis-prompt", "api/visits/round-summary"}
UNAVAILABLE = {"api/consent/confirm", "api/consent/request", "api/paste", "api/prompt", "api/property/extract",
               "api/property/parse", "api/property/prompt", "api/property/save", "api/recipient", "api/visits/close",
               "api/visits/round-generate", "api/visits/round-individual", "api/visits/round-paste",
               "api/visits/round-prompt", "api/visits/round-save",
               # 29/09: the Oficina (admin only): never in the sales demo
               "api/ai/price", "api/ai/reviewer", "api/review", "api/prompts/common", "api/ai/context", "api/ai/limits", "api/testlab/state", "api/testlab/contest", "api/testlab/clients",
               "api/testlab/consultant", "api/testlab/wipe", "api/testlab/advance"}


@pytest.fixture(scope="module")
def site(tmp_path_factory):
    folder, archive = build(tmp_path_factory.mktemp("webdemo") / "demo")
    return folder, archive


def data_of(folder):
    text = (folder / "demo-data.js").read_text(encoding="utf-8")
    return text, json.loads(text[text.index("{"):text.rindex("}") + 1])


def run_scenario(folder, *extra):
    result = subprocess.run([str(JSC), str(HERE / "harness.js"), str(folder / "demo-data.js"), *map(str, extra),
                             str(folder / "demo-api.js"), str(HERE / "scenario.js")],
                            capture_output=True, text=True, timeout=60)
    return json.loads(result.stdout.strip().splitlines()[-1])


def test_the_demo_is_a_folder_of_plain_files_ready_to_upload(site):
    folder, archive = site
    page = (folder / "index.html").read_text(encoding="utf-8")
    assert "{{" not in page and "nonce" not in page
    assert page.index("demo-data.js") < page.index("demo-api.js") < page.index('src="app.js"')
    assert (folder / "app.js").read_bytes() == (ROOT / "frontend" / "app.js").read_bytes()  # the page as it is
    for name in ("style.css", "demo.css", "contactos.csv", "LEIA-ME.txt", "themes/racing.css"):
        assert (folder / name).is_file()
    with zipfile.ZipFile(archive) as bundle:
        assert {"index.html", "app.js", "demo-api.js", "demo-data.js"} <= set(bundle.namelist())


def test_the_demo_holds_only_fictitious_data(site):
    folder, _ = site
    text, data = data_of(folder)
    addresses = set(re.findall(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", text + (folder / "contactos.csv").read_text("utf-8")))
    assert addresses and all(a.endswith((".example", "@example.com")) or a == "reply@idealista.pt" for a in addresses)
    assert not re.search(r"APalace|AP_BMH|Ramada|gmail\.com", text)
    assert len(data["stages"]) == 4 and data["generated"]


def test_every_call_of_the_page_is_answered_or_said_to_need_the_full_version(site):
    folder, _ = site
    calls = set(re.findall(r"call\('(api/[a-z/_-]*[a-z_-])", (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")))
    shim = (folder / "demo-api.js").read_text(encoding="utf-8")
    handled = set(re.findall(r"'(?:POST |GET )?(api/[a-z/_-]+)'", shim))
    _, data = data_of(folder)
    recorded = {key.split("|")[0] for key in data["stages"][0]}
    assert RECORDED <= recorded
    # call('api/selection/' + action): a prefix, answered when each of its actions is
    missing = {path for path in calls - handled - recorded - UNAVAILABLE
               if not any(known.startswith(path + "/") for known in handled)}
    assert not missing, f"Chamadas da página sem resposta na demonstração: {sorted(missing)}"


@pytest.mark.skipif(not JSC.exists(), reason="sem o JavaScriptCore do macOS")
def test_the_demo_steps_run_from_reading_to_sending(site):
    folder, _ = site
    result = run_scenario(folder)
    assert result["failures"] == []
    facts = result["facts"]
    assert (facts["opening"], facts["added"], facts["afterRead"]) == (5, 5, 10)
    assert (facts["saved"], facts["preview"], facts["sent"], facts["lisboaLeft"]) == (3, 3, 3, 0)


@pytest.mark.skipif(not JSC.exists(), reason="sem o JavaScriptCore do macOS")
def test_the_dates_follow_the_day_the_demo_is_shown(site, tmp_path):
    folder, _ = site
    _, data = data_of(folder)
    before = run_scenario(folder)["facts"]
    earlier = tmp_path / "earlier.js"  # as if the demo had been built three days before today
    day = data["build_day"]
    from datetime import date, timedelta
    earlier.write_text(f'DEMO_DATA.build_day = "{date.fromisoformat(day) - timedelta(days=3)}";')
    after = run_scenario(folder, earlier)
    assert after["failures"] == []
    moved = lambda at: (date.fromisoformat(at[:10]) + timedelta(days=3)).isoformat() + at[10:]
    assert after["facts"]["slots"] == [moved(at) for at in before["slots"]]
    assert after["facts"]["lastRead"] == moved(before["lastRead"])
