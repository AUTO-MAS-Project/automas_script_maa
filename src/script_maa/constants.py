from __future__ import annotations

from datetime import timedelta, timezone

UTC4 = timezone(timedelta(hours=4))
UTC8 = timezone(timedelta(hours=8))

TASK_MODE_ZH = {
    "AutoProxy": "自动代理",
    "ManualReview": "人工排查",
    "ScriptConfig": "脚本配置",
}

MAA_RUN_MOOD_BOOK = {"Annihilation": "剿灭", "Routine": "日常"}

MAA_TASKS = ["StartUp", "Fight", "Infrast", "Recruit", "Mall", "Award", "Roguelike"]

MAA_TASKS_ZH = [
    "开始唤醒",
    "理智作战",
    "基建换班",
    "自动公招",
    "信用收支",
    "领取奖励",
    "自动肉鸽",
]

MAA_TASK_OPTIONS = [
    {"label": "开始唤醒", "value": "StartUp"},
    {"label": "理智作战", "value": "Fight"},
    {"label": "基建换班", "value": "Infrast"},
    {"label": "公开招募", "value": "Recruit"},
    {"label": "信用收支", "value": "Mall"},
    {"label": "领取奖励", "value": "Award"},
    {"label": "肉鸽", "value": "Roguelike"},
    {"label": "生息演算", "value": "Reclamation"},
]

MAA_STAGE_KEY = [
    "MedicineNumb",
    "SeriesNumb",
    "Stage",
    "Stage_1",
    "Stage_2",
    "Stage_3",
    "Stage_Remain",
]

ARKNIGHTS_PACKAGE_NAME = {
    "Official": "com.hypergryph.arknights",
    "Bilibili": "com.hypergryph.arknights.bilibili",
    "YoStarEN": "com.YoStarEN.Arknights",
    "YoStarJP": "com.YoStarJP.Arknights",
    "YoStarKR": "com.YoStarKR.Arknights",
    "txwy": "tw.txwy.and.arknights",
}

MAA_TASK_TRANSITION_METHOD_BOOK = {
    "NoAction": "8",
    "ExitGame": "9",
    "ExitEmulator": "9",
}

MAA_STARTUP_BASE = {
    "$type": "StartUpTask",
    "AccountName": "",
    "Name": "开始唤醒",
    "IsEnable": True,
    "TaskType": "StartUp",
}

MAA_ANNIHILATION_FIGHT_BASE = {
    "$type": "FightTask",
    "UseMedicine": False,
    "MedicineCount": 0,
    "UseStone": False,
    "StoneCount": 0,
    "EnableTargetDrop": False,
    "DropId": "",
    "DropCount": 0,
    "EnableTimesLimit": False,
    "TimesLimit": 999,
    "Series": 0,
    "StagePlan": ["Annihilation"],
    "IsDrGrandet": False,
    "UseExpiringMedicine": True,
    "UseCustomAnnihilation": True,
    "AnnihilationStage": "Annihilation",
    "HideUnavailableStage": True,
    "IsStageManually": False,
    "UseOptionalStage": False,
    "UseStoneAllowSave": False,
    "HideSeries": False,
    "UseWeeklySchedule": False,
    "WeeklySchedule": {
        "Sunday": True,
        "Monday": True,
        "Tuesday": True,
        "Wednesday": True,
        "Thursday": True,
        "Friday": True,
        "Saturday": True,
    },
    "Name": "剿灭作战",
    "IsEnable": True,
    "TaskType": "Fight",
}

MAA_REMAIN_FIGHT_BASE = {
    "$type": "FightTask",
    "UseMedicine": False,
    "MedicineCount": 0,
    "UseStone": False,
    "StoneCount": 0,
    "EnableTargetDrop": False,
    "DropId": "",
    "DropCount": 0,
    "EnableTimesLimit": False,
    "TimesLimit": 999,
    "Series": 0,
    "StagePlan": [""],
    "IsDrGrandet": False,
    "UseExpiringMedicine": False,
    "UseCustomAnnihilation": False,
    "AnnihilationStage": "Annihilation",
    "HideUnavailableStage": True,
    "IsStageManually": True,
    "UseOptionalStage": False,
    "UseStoneAllowSave": False,
    "HideSeries": False,
    "UseWeeklySchedule": False,
    "WeeklySchedule": {
        "Sunday": True,
        "Monday": True,
        "Tuesday": True,
        "Wednesday": True,
        "Thursday": True,
        "Friday": True,
        "Saturday": True,
    },
    "Name": "剩余理智",
    "IsEnable": True,
    "TaskType": "Fight",
}

RESOURCE_STAGE_INFO = [
    {"value": "-", "text": "禁用", "days": [1, 2, 3, 4, 5, 6, 7]},
    {"value": "*", "text": "当前/上次", "days": [1, 2, 3, 4, 5, 6, 7]},
    {"value": "1-7", "text": "1-7", "days": [1, 2, 3, 4, 5, 6, 7]},
    {"value": "R8-11", "text": "R8-11", "days": [1, 2, 3, 4, 5, 6, 7]},
    {"value": "12-17-HARD", "text": "12-17-HARD", "days": [1, 2, 3, 4, 5, 6, 7]},
    {"value": "LS-6", "text": "经验-6/5", "days": [1, 2, 3, 4, 5, 6, 7]},
    {"value": "CE-6", "text": "龙门币-6/5", "days": [2, 4, 6, 7]},
    {"value": "AP-5", "text": "红票-5", "days": [1, 4, 6, 7]},
    {"value": "CA-5", "text": "技能-5", "days": [2, 3, 5, 7]},
    {"value": "SK-5", "text": "碳-5", "days": [1, 3, 5, 6]},
    {"value": "PR-A-1", "text": "近卫芯片", "days": [1, 4, 5, 7]},
    {"value": "PR-A-2", "text": "近卫芯片组", "days": [1, 4, 5, 7]},
    {"value": "PR-B-1", "text": "狙击芯片", "days": [1, 2, 5, 6]},
    {"value": "PR-B-2", "text": "狙击芯片组", "days": [1, 2, 5, 6]},
    {"value": "PR-C-1", "text": "术师芯片", "days": [3, 4, 6, 7]},
    {"value": "PR-C-2", "text": "术师芯片组", "days": [3, 4, 6, 7]},
    {"value": "PR-D-1", "text": "特种芯片", "days": [2, 3, 6, 7]},
    {"value": "PR-D-2", "text": "特种芯片组", "days": [2, 3, 6, 7]},
]
