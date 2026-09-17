import json
import os
from dataclasses import dataclass, field

TASKS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tasks")


@dataclass
class Sample:
    id: str
    state: object
    label: dict


@dataclass
class Task:
    id: str
    name: str
    description: str
    primary_question: str
    questions: dict
    samples: list = field(default_factory=list)

    def state_for_display(self, sample):
        if isinstance(sample.state, str):
            return sample.state
        return json.dumps(sample.state)


def load_task(path):
    with open(path) as fh:
        data = json.load(fh)
    return Task(
        id=data["id"],
        name=data["name"],
        description=data.get("description", ""),
        primary_question=data["primary_question"],
        questions=data["questions"],
        samples=[Sample(id=s["id"], state=s["state"], label=s["label"]) for s in data["samples"]],
    )


def load_tasks(selected=None):
    tasks = {}
    for filename in sorted(os.listdir(TASKS_DIR)):
        if not filename.endswith(".json"):
            continue
        task = load_task(os.path.join(TASKS_DIR, filename))
        tasks[task.id] = task
    if selected in (None, "all"):
        return tasks
    wanted = [t.strip() for t in selected.split(",") if t.strip()]
    return {tid: tasks[tid] for tid in wanted if tid in tasks}


def label_to_reference(qtype, label_value):
    if label_value in (None, ""):
        return ""
    if qtype == "noul":
        return "yes" if bool(label_value) else "no"
    if qtype == "score":
        return str(int(label_value))
    return str(label_value)