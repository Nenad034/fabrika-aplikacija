import json
import uuid
from typing import List, Optional, Dict
from pathlib import Path
from pydantic import BaseModel, Field

class Agent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    role: str  # System Prompt
    model: str = "gpt-4o-mini"
    color: str = "blue"
    is_active: bool = True

class AgentManager:
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.agents_dir = self.base_dir / ".agent"
        self.agents_file = self.agents_dir / "agents.json"
        self.agents: List[Agent] = []
        
        self._load_agents()

    def _load_agents(self):
        """Loads agents from agents.json or creates defaults."""
        if not self.agents_file.exists():
            self._create_defaults()
        else:
            try:
                data = json.loads(self.agents_file.read_text(encoding='utf-8'))
                self.agents = [Agent(**item) for item in data]
            except Exception as e:
                print(f"[AgentManager] Error loading agents: {e}")
                self._create_defaults()
    
    def _create_defaults(self):
        """Creates default agents if none exist."""
        defaults = [
            Agent(name="Glavni Arhitekta", role="Ti si iskusni softverski arhitekta. Fokusiraj se na strukturu, design pattern-e i skalabilnost.", model="gemini/gemini-3-flash-preview", color="blue"),
            Agent(name="Senior Developer", role="Ti si Senior Developer. Tvoj kod je efikasan, čist i prati najbolje prakse.", model="gemini/gemini-3-flash-preview", color="green"),
            Agent(name="QA Tester", role="Ti si QA Inženjer. Tvoj zadatak je da pronađeš potencijalne bugove i predložiš testove.", model="gemini/gemini-3-flash-preview", color="red", is_active=False)
        ]
        self.agents = defaults
        self.save_agents()
    
    def save_agents(self):
        """Saves current agents list to json."""
        self.agents_dir.mkdir(parents=True, exist_ok=True)
        data = [agent.dict() for agent in self.agents]
        self.agents_file.write_text(json.dumps(data, indent=2), encoding='utf-8')
        print(f"[AgentManager] Agents saved to {self.agents_file}")

    def get_agent(self, agent_id: str) -> Optional[Agent]:
        for agent in self.agents:
            if agent.id == agent_id:
                return agent
        return None

    def add_agent(self, agent: Agent):
        self.agents.append(agent)
        self.save_agents()

    def update_agent(self, agent_id: str, updates: Dict):
        agent = self.get_agent(agent_id)
        if agent:
            # Pydantic v1 style update, v2 uses model_copy(update=...)
            for key, value in updates.items():
                if hasattr(agent, key):
                    setattr(agent, key, value)
            self.save_agents()
            return True
        return False

    def delete_agent(self, agent_id: str):
        self.agents = [a for a in self.agents if a.id != agent_id]
        self.save_agents()
    
    def get_active_agents(self) -> List[Agent]:
        return [a for a in self.agents if a.is_active]
