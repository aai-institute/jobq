from enum import Enum


class ImagePullPolicy(Enum):
    ALWAYS = "Always"
    NEVER = "Never"
    IFNOTPRESENT = "IfNotPresent"


class Image:
    def __init__(
        self, tag: str, pull_policy: ImagePullPolicy = ImagePullPolicy.ALWAYS
    ) -> None:
        self.tag = tag
        self.pull_policy = pull_policy
