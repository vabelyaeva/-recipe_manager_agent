import operator
from typing import Annotated, Optional

from langchain.messages import AnyMessage
from typing_extensions import TypedDict


class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]
    active_collection_id: Optional[int]
    active_collection_name: Optional[str]
    active_recipe_id: Optional[int]
    active_recipe_name: Optional[str]
    last_listed_recipe_ids: list[int]