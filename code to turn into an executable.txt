py -3.12 -m venv .venv312
.venv312\Scripts\activate
python -V
python -m pip install --upgrade pip
python -m pip install pyinstaller==6.6 pillow tkhtmlview requests rarfile pywin32

Remove-Item -Recurse -Force .\build, .\dist -ErrorAction SilentlyContinue
python -m PyInstaller --clean --noconfirm realms_launcher.spec

OR:

py -3.12 -m venv .venv312
.venv312\Scripts\activate
python -V
python -m pip install --upgrade pip
python -m pip install pyinstaller==6.6 pillow tkhtmlview requests rarfile pywin32

Remove-Item -Recurse -Force .\build, .\dist -ErrorAction SilentlyContinue
python -m PyInstaller --clean --noconfirm --onefile --noconsole --noupx `
  --icon aotr_fs.ico `
  --add-data "aotr_fs.ico;." `
  --add-data "banner.png;." `
  --add-data "background.jpg;." `
  --add-data "icons8-one-ring-96.png;." `
  --add-data "SCCpointer.cur;." `
  --add-data "SCCRepair.ani;." `
  --add-data "SCCAttMagic.ani;." `
  --add-data "magnify.ani;." `
  --add-data "OneRing.ani;." `
  --add-data "ringbearer;ringbearer" `
  --add-binary "C:\Windows\System32\vcruntime140.dll;." `
  --add-binary "C:\Windows\System32\vcruntime140_1.dll;." `
  --add-binary "C:\Windows\System32\msvcp140.dll;." `
  realms_launcher.py