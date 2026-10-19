# 发布后 CI 编码与结果状态收尾

原收尾任务和BLOCKED_WITH_EVIDENCE结果保持，原发布9620072414d863e8cfb070fe68b3946898bfe85f及Publisher回执不改。本次仅处理新提交Actions 39275990425实际失败，不新跑20图、不改运行模型/规则、日用库、main或Notion。

编辑前在干净9620072基线上启动独立Publisher事务01a15438-c239-7293-85e8-197fcac94b0b，Git-only，原基线/历史不重绑。已读取原失败及原收尾回执，确认这是CI测试传输与旧完成断言，不能用放宽产品门槛处理。

Windows失败为两项参照receipt硬退出用例：子进程指定-X utf8，父进程默认cp1252/cp950解码，reader线程UnicodeDecodeError后stderr为None。父进程显式-X utf8=0复现2FAIL；修改调用方明确encoding='utf8'，保留成功重用、零重复与原图变更必须拒绝的全部断言。

browser原报告41PASS/1FAIL：手动导入一份无真实覆盖的合成包却断言Job成功，和本轮冻结完成契约相矛盾。保留任务建立、下载、原图导入、人工pending/review断言，改为blocked/partial及本包引用数量。

验证：父进程禁用UTF-8模式，完整收尾恢复套件14 PASS，浏览器合成导入路径1 PASS。命令分别为`.venv\Scripts\python.exe -X utf8=0 -m pytest -q --basetemp "D:\AI PROJECTS\photography-reference-lab\.local\cu2" tests/test_collection_finalization.py --junitxml=.local/finalization/ci-locale-fixed.xml`及同Python参数下单独运行`tests/test_browser.py::test_browser_notes_collection_download_import`（basetemp `.local/cb1`，回执`ci-browser-fixed.xml`）。原复现2 FAIL和远端失败日志保留。

收口只含两个测试文件及两份任务文档，不改运行代码。原Actions 39275990425实际结论仍为FAIL（core 3.11/3.13通过，Windows两项测试流解码及browser旧成功断言失败）；修正提交的新Actions需按真实状态查看，不预写通过。远端提交及Publisher状态以本次保存回执为准。

用户要求收口后提供Git仓库讨论，本轮停止继续搜图、模型调用与扩展修复。原真实任务依然0/20、BLOCKED_WITH_EVIDENCE；14+1项本地通过仅验证本次测试修正，不代替20图领域验收。未合并main、未切日用环境、未写Notion。
