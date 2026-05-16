# RiskPulse — Third-party Notices

RiskPulse incorporates the following open-source components. Each is used
in accordance with its license. The full text of each license is available
from the upstream project.

| Component        | Version   | License           | Upstream                                            |
| ---------------- | --------- | ----------------- | --------------------------------------------------- |
| Python           | 3.12+     | PSF-2.0           | https://www.python.org                              |
| PySide6          | 6.6+      | LGPL-3.0          | https://doc.qt.io/qtforpython-6                     |
| spaCy            | 3.7+      | MIT               | https://spacy.io                                    |
| fr_core_news_sm  | 3.8       | CC-BY-SA-4.0      | https://spacy.io/models/fr                          |
| en_core_web_sm   | 3.8       | MIT               | https://spacy.io/models/en                          |
| NetworkX         | 3.0+      | BSD-3-Clause      | https://networkx.org                                |
| scikit-learn     | 1.3+      | BSD-3-Clause      | https://scikit-learn.org                            |
| NumPy            | 1.24+     | BSD-3-Clause      | https://numpy.org                                   |
| pandas           | 2.0+      | BSD-3-Clause      | https://pandas.pydata.org                           |
| SciPy            | 1.10+     | BSD-3-Clause      | https://scipy.org                                   |
| FastAPI          | 0.110+    | MIT               | https://fastapi.tiangolo.com                        |
| Uvicorn          | 0.29+     | BSD-3-Clause      | https://www.uvicorn.org                             |
| Pydantic         | 2.5+      | MIT               | https://docs.pydantic.dev                           |
| deep-translator  | 1.11+     | MIT               | https://github.com/nidhaloff/deep-translator        |
| PyVis            | 0.3+      | BSD-3-Clause      | https://github.com/WestHealth/pyvis                 |
| ReportLab        | 4.0+      | BSD-3-Clause      | https://www.reportlab.com                           |
| pypdf            | 4.0+      | BSD-3-Clause      | https://pypdf.readthedocs.io                        |
| python-dateutil  | 2.8+      | Apache-2.0        | https://github.com/dateutil/dateutil                |
| BeautifulSoup4   | 4.12+     | MIT               | https://www.crummy.com/software/BeautifulSoup       |
| JetBrains Mono   | 2.304     | OFL-1.1           | https://www.jetbrains.com/lp/mono                   |
| vis.js (network) | 9.1+      | Apache-2.0        | https://visjs.org                                   |

## LGPL note — PySide6

PySide6 is distributed under the LGPL-3.0. By embedding PySide6 in RiskPulse,
the obligation to provide the means to relink against a modified PySide6 is
satisfied by the fact that the bundle ships standard, unmodified PySide6
binaries (separately replaceable in the `_internal/PySide6/` directory of the
installation). No modification has been made to the PySide6 source.

## Trademarks

RiskPulse is a trademark of C. Abdoulaye. All other trademarks are the
property of their respective owners.

For licensing inquiries : contact@riskpulse.io
