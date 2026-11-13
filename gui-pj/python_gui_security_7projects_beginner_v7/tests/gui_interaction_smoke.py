"""Exercise real Tkinter widgets and button callbacks under a display.

Run: xvfb-run -a python3 tests/gui_interaction_smoke.py
"""
import importlib.util
import shutil
import tempfile
import tkinter as tk
from pathlib import Path
from tkinter import ttk
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
real_tk = tk.Tk


def widgets(parent, target):
    result = []
    for child in parent.winfo_children():
        if isinstance(child, target):
            result.append(child)
        result.extend(widgets(child, target))
    return result


def button(root, label):
    found = [item for item in widgets(root, ttk.Button) if item.cget('text') == label]
    if len(found) != 1:
        raise AssertionError(f'Expected one button {label}: {len(found)}')
    return found[0]


def source(number):
    target = next((ROOT / 'projects').glob(number + '_*.py'))
    spec = importlib.util.spec_from_file_location('gui_real_' + number, target)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run(number, probe, filename=None):
    module = source(number)
    errors = []
    def fake_tk():
        root = real_tk()
        def later():
            try:
                probe(root)
            except Exception as exc:
                errors.append(exc)
            finally:
                root.destroy()
        root.after(80, later)
        return root
    dialog = filename if filename else str(ROOT/'samples/auth_events.csv')
    with patch.object(tk, 'Tk', side_effect=fake_tk), patch.object(module.filedialog, 'askopenfilename', return_value=dialog) if hasattr(module, 'filedialog') else patch.object(tk, 'Tk', side_effect=fake_tk):
        # We patch Tk twice for modules without filedialog; the identical side effect is fine.
        module.launch()
    if errors:
        raise AssertionError(f'{number} interaction failed: {errors[0]}') from errors[0]
    print('GUI INTERACTION PASS',number)


def probe01(root):
    button(root,'Open CSV').invoke()
    tree=widgets(root,ttk.Treeview)[0]
    assert len(tree.get_children()) == 6
    entries=widgets(root,ttk.Entry)
    entries[0].insert(0,'bob')
    root.update_idletasks()
    assert len(tree.get_children()) == 2


def probe02(root):
    texts=widgets(root,tk.Text)
    texts[0].delete('1.0','end')
    texts[0].insert('1.0',(ROOT/'samples/response_headers.txt').read_text())
    button(root,'Analyze headers').invoke()
    answer=texts[1].get('1.0','end')
    assert 'Missing content-security-policy' in answer and 'Missing HSTS' in answer
    texts[0].delete('1.0','end')
    texts[0].insert('1.0','Set-Cookie: sid=x; SameSite=\n')
    button(root,'Analyze headers').invoke()
    assert 'valid samesite' in texts[1].get('1.0','end')


def probe03(root):
    button(root,'Open rule CSV').invoke()
    table=widgets(root,ttk.Treeview)[0]
    assert table.winfo_manager() == 'pack' and table.winfo_ismapped()
    assert len(table.get_children()) == 5
    assert any('REVIEW' in str(table.item(row,'values')) for row in table.get_children())
    assert widgets(root,ttk.Scrollbar), 'Expected vertical scrollbar'


def probe04(root):
    entries=widgets(root,ttk.Entry)
    assert len(entries) == 2
    for field,path in zip(entries,['indicators.csv','ioc_events.csv']):
        field.insert(0,str(ROOT/'samples'/path))
    button(root,'Correlate').invoke()
    assert len(widgets(root,ttk.Treeview)[0].get_children()) == 3


def probe05(root):
    with tempfile.TemporaryDirectory() as temp:
        folder=Path(temp)/'working'
        shutil.copytree(ROOT/'samples/integrity_folder',folder)
        entries=widgets(root,ttk.Entry)
        entries[0].insert(0,str(folder))
        button(root,'Capture baseline').invoke()
        (folder/'config.txt').write_text('change\n',encoding='utf-8')
        button(root,'Compare now').invoke()
        states=[widgets(root,ttk.Treeview)[0].item(item,'values')[1] for item in widgets(root,ttk.Treeview)[0].get_children()]
        assert 'MODIFIED' in states


def probe06(root):
    texts=widgets(root,tk.Text)
    texts[0].delete('1.0','end')
    texts[0].insert('1.0',(ROOT/'samples/mail_headers.txt').read_text())
    button(root,'Review headers').invoke()
    assert 'differs' in texts[1].get('1.0','end')


def probe07(root):
    for _ in range(3): button(root,'Simulate FAIL').invoke()
    button(root,'Simulate SUCCESS').invoke()
    for _ in range(3): button(root,'Advance +10s').invoke()
    button(root,'Simulate SUCCESS').invoke()
    out=widgets(root,tk.Text)[0].get('1.0','end')
    assert 'LOCKED' in out and 'BLOCKED' in out and 'Allowed' in out


if __name__ == '__main__':
    for number,probe,filename in [
        ('01',probe01,ROOT/'samples/auth_events.csv'),('02',probe02,None),
        ('03',probe03,ROOT/'samples/firewall_rules.csv'),('04',probe04,None),
        ('05',probe05,None),('06',probe06,None),('07',probe07,None),
    ]:
        run(number,probe,filename)
