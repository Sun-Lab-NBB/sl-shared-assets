---
name: experiment-design
description: >-
  Interactive guidance for building Sun lab experiment configurations using MCP tools. Covers cue
  and segment design, trial structure configuration, and experiment state definition.
---

# Experiment Design Skill

This skill provides guidance for interactively building Sun lab experiment configurations using the MCP tools
exposed by this library. Use this skill when helping users design new experiments or modify existing ones.

---

## MCP Server

Start the MCP server with: `sl-configure mcp`

---

## Interactive Design Workflow

When designing experiment configurations, follow this conversational workflow:

### 1. Understand the Experiment Goals

Ask the user:
- What is the scientific question or behavioral paradigm?
- What type of trials will be used (water reward, gas puff, or both)?
- How many experimental phases/states are needed?
- What existing configurations (if any) should serve as a reference?

### 2. Design Visual Environment (Cues and Segments)

Guide the user through cue design:
- Each cue needs: name, unique code (0-255), length in cm
- Common patterns: Gray (placeholder), A-H (visual patterns)
- Typical cue lengths: 30-50 cm

Guide the user through segment design:
- Segments are sequences of cues
- Name should describe the sequence (e.g., "Segment_abcd")
- Consider visual distinctiveness for the animal

### 3. Configure Trial Structures

For water reward (reinforcing) trials:
- Define stimulus trigger zone boundaries (start_cm, end_cm)
- Set stimulus location (collision boundary)
- Configure reward size (typical: 5 microliters)
- Set reward tone duration (typical: 300 ms)

For gas puff (aversive) trials:
- Define stimulus trigger zone boundaries
- Set stimulus location
- Configure puff duration (typical: 100 ms)
- Set occupancy duration threshold (typical: 1000 ms)

### 4. Define Experiment States

Common state patterns:
- **baseline**: No trials, imaging only (600s typical)
- **experiment**: Active trials with rewards/punishments (3000s typical)
- **cooldown**: No trials, post-experiment imaging (600s typical)

For each state, configure:
- State duration in seconds
- Whether trials are active
- Guidance parameters for both trial types

### 5. Validate Configuration

Always validate the final configuration using `validate_experiment_configuration_tool`.

---

## MCP Tools Reference

### Setup Tools

| Tool                               | Description                            |
|------------------------------------|----------------------------------------|
| `set_working_directory_tool`       | Sets the local working directory       |
| `create_project_tool`              | Creates a new project structure        |
| `create_experiment_template_tool`  | Creates an empty experiment template   |

### Configuration Tools

| Tool                           | Description                       |
|--------------------------------|-----------------------------------|
| `add_cue_tool`                 | Adds a visual cue                 |
| `remove_cue_tool`              | Removes a visual cue              |
| `add_segment_tool`             | Adds a segment (cue sequence)     |
| `remove_segment_tool`          | Removes a segment                 |
| `add_water_reward_trial_tool`  | Adds a reinforcing trial          |
| `add_gas_puff_trial_tool`      | Adds an aversive trial            |
| `remove_trial_tool`            | Removes a trial structure         |
| `add_experiment_state_tool`    | Adds an experiment state          |
| `update_experiment_state_tool` | Modifies an existing state        |
| `remove_experiment_state_tool` | Removes a state                   |
| `set_vr_environment_tool`      | Configures VR corridor settings   |
| `set_experiment_metadata_tool` | Sets scene name and offset        |

### Query Tools

| Tool                                     | Description                   |
|------------------------------------------|-------------------------------|
| `read_experiment_configuration_tool`     | Reads full config summary     |
| `list_experiment_cues_tool`              | Lists all defined cues        |
| `list_experiment_segments_tool`          | Lists all segments            |
| `list_experiment_trials_tool`            | Lists all trial structures    |
| `list_experiment_states_tool`            | Lists all states              |
| `validate_experiment_configuration_tool` | Validates completeness        |

---

## Example Configuration Structure

```yaml
unity_scene_name: "ExperimentName"
cue_offset_cm: 10.0

cues:
  - name: "Gray"
    code: 0
    length_cm: 30.0
  - name: "A"
    code: 1
    length_cm: 50.0

segments:
  - name: "Segment_abc"
    cue_sequence: ["A", "Gray", "B", "Gray", "C"]

vr_environment:
  corridor_spacing_cm: 20.0
  segments_per_corridor: 3
  padding_prefab_name: "Padding"
  cm_per_unity_unit: 10.0

trial_structures:
  reward_trial:
    segment_name: "Segment_abc"
    stimulus_trigger_zone_start_cm: 168.0
    stimulus_trigger_zone_end_cm: 192.0
    stimulus_location_cm: 188.0
    reward_size_ul: 5.0
    reward_tone_duration_ms: 300

experiment_states:
  baseline:
    experiment_state_code: 1
    system_state_code: 1
    state_duration_s: 600.0
    supports_trials: false
  experiment:
    experiment_state_code: 2
    system_state_code: 2
    state_duration_s: 3000.0
    supports_trials: true
    reinforcing_initial_guided_trials: 3
    reinforcing_recovery_failed_threshold: 6
    reinforcing_recovery_guided_trials: 3
```

---

## Reference Configurations

Valid configuration examples are available in the sl-unity-tasks repository:
- `Assets/InfiniteCorridorTask/Configurations/MF_Reward.yaml` - Cyclic 8-cue reward task
- `Assets/InfiniteCorridorTask/Configurations/MF_Aversion_Reward.yaml` - Combined aversion/reward task
- `Assets/InfiniteCorridorTask/Configurations/SSO_*.yaml` - Various sequence learning tasks

---

## Best Practices

1. **Start with a template**: Use `create_experiment_template_tool` to create a minimal starting point
2. **Build incrementally**: Add cues, then segments, then trials, then states
3. **Validate often**: Use `validate_experiment_configuration_tool` after major changes
4. **Ask clarifying questions**: When in doubt, ask the user about their experimental design
5. **Reference existing configs**: Point users to similar existing configurations for guidance
