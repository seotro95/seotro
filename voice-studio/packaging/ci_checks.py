"""Bound native regression checks and publish actionable, credential-free failures."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def child(report):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    import pytest
    state = {'current': None, 'passed': 0, 'failed': [], 'skipped': 0}
    def save():
        report.write_text(json.dumps(state, ensure_ascii=False), encoding='utf-8')
    class Reporter:
        def pytest_runtest_logstart(self, nodeid, location):
            state['current'] = nodeid
            save()
        def pytest_runtest_logreport(self, report):
            if report.failed:
                state['failed'].append({'test': report.nodeid, 'detail': str(report.longrepr)[-10000:]})
            elif report.when == 'call' and report.passed:
                state['passed'] += 1
            elif report.skipped:
                state['skipped'] += 1
            save()
    return pytest.main(['-q', '-o', 'faulthandler_timeout=60'], plugins=[Reporter()])


def main():
    if len(sys.argv)>1 and sys.argv[1] == '--child':
        return child(Path(sys.argv[2]))
    with tempfile.TemporaryDirectory() as folder:
        report = Path(folder)/'report.json'
        process = subprocess.Popen([sys.executable, __file__, '--child', str(report)])
        try:
            code = process.wait(timeout=150)
        except subprocess.TimeoutExpired:
            if os.name == 'nt':
                subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'], check=False)
            else:
                process.kill()
            process.wait()
            code = 124
        state = json.loads(report.read_text(encoding='utf-8')) if report.exists() else {}
    summary = f'Regression: {state.get("passed",0)} passed, {len(state.get("failed",[]))} failed, {state.get("skipped",0)} skipped. Last test: {state.get("current")}. Exit: {code}.'
    print(summary, flush=True)
    if code:
        def annotate(message):
            safe = message.replace('%','%25').replace('\r','%0D').replace('\n','%0A')
            print('::error title=Windows regression::'+safe, flush=True)
        annotate(summary)
        for failure in state.get('failed',[]):
            annotate(failure['test']+'\n'+failure['detail'])
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'],'a',encoding='utf-8') as output:
            output.write('## Windows regression checks\n'+summary+'\n')
            for failure in state.get('failed',[]):
                output.write('\n### '+failure['test']+'\n```text\n'+failure['detail']+'\n```\n')
    return code


if __name__ == '__main__':
    sys.exit(main())
