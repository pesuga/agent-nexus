# Product Requirements Document (PRD)
## Agent Nexus: Central Hub for AI Agent Orchestration
**Version**: 1.0  
**Date**: 2026-03-01  
**Status**: Active Development  
**Author**: Claw (AI Assistant)  
**Stakeholders**: Pesu (Primary User), AI Agent Team (Ren, Aki, Kuro, Shin, Sora)

---

## Executive Summary

This document outlines the requirements for a custom kanban system designed specifically for AI agent orchestration. The system emerged as a response to the complexity and limitations of existing solutions (Plane integration, Vibe Kanban), aiming to provide a simple, self-contained, and reliable workflow management tool for coordinating AI agents.

### Problem Statement
Existing solutions for AI agent task management suffer from:
1. **Complex Integration**: Plane API/webhook integration requires extensive configuration and suffers from permission/connectivity issues
2. **Dependency Hell**: Vibe Kanban requires complex Rust toolchains, Docker, and multiple dependencies
3. **Lack of Control**: External systems introduce reliability issues and limited customization
4. **Agent Coordination Gaps**: No system specifically designed for the unique needs of AI agent teams (crash recovery, heartbeat monitoring, specialized workflows)

### Solution Vision
A lightweight, self-hosted kanban system built from the ground up for AI agent orchestration, featuring:
- Simple web interface with drag-and-drop functionality
- Real-time synchronization between agents
- Built-in crash recovery and heartbeat monitoring
- No external dependencies beyond basic Python/JavaScript
- Custom workflows optimized for AI agent collaboration

---

## Background & Context

### Historical Journey
1. **Plane Integration Phase** (2026-02-27 to 2026-03-01)
   - Built webhook system to detect task assignments in Plane
   - Created HTTP runner service for spawning OpenClaw agents
   - Achieved functional integration but faced API permission issues
   - Complexity grew with each layer added (k3s, HTTPS, authentication)

2. **Vibe Kanban Exploration** (2026-03-01)
   - Investigated BloopAI's Vibe Kanban as alternative
   - Encountered Rust toolchain compatibility issues (edition2024 not supported)
   - Docker build failures and complex dependency requirements
   - Realized external solutions introduce their own complexity

3. **Pivot to Custom Solution** (2026-03-01)
   - User feedback: "I feel this approach is getting more and more complicated and not going anywhere"
   - Decision to build simple, custom solution tailored to specific needs
   - Focus on simplicity, reliability, and direct control

### Current State
The **Agent Task Manager** has been developed as the custom solution, featuring:
- ✅ **Backend**: FastAPI + SQLite (port 8000)
- ✅ **Frontend**: Drag-and-drop kanban with real-time updates
- ✅ **CLI**: Command-line interface for agent interaction
- ✅ **Documentation**: Comprehensive guides and examples
- ✅ **Agent Integration**: Support for Ren, Aki, Kuro, Shin, Sora roles

However, **agents fail to complete tasks** due to integration gaps between the kanban system and actual agent execution.

---

## Product Requirements

### 1. Core Requirements

#### 1.1 Task Management
- **Must Have**:
  - Create, read, update, delete tasks
  - Drag-and-drop task movement between columns
  - Task prioritization (High/Medium/Low)
  - Assign tasks to specific agents
  - Task descriptions and metadata
  - Real-time updates across all connected clients

- **Should Have**:
  - Task templates for common workflows
  - Bulk operations
  - Task dependencies
  - Due dates and reminders

#### 1.2 Agent Coordination
- **Must Have**:
  - Agent status monitoring (online/offline/working)
  - Task assignment to specific agent roles
  - Agent heartbeat system for crash detection
  - Automatic task reassignment on agent failure
  - Agent-specific workflows and capabilities

- **Should Have**:
  - Agent performance metrics
  - Load balancing across agents
  - Agent specialization tags
  - Collaborative task handling

#### 1.3 Workflow Management
- **Must Have**:
  - Customizable kanban columns
  - Status transitions (Backlog → Todo → In Progress → Review → Done)
  - Workflow rules and constraints
  - State-based task filtering

- **Should Have**:
  - Multiple project boards
  - Board templates
  - Workflow automation rules
  - Integration with external triggers

### 2. Technical Requirements

#### 2.1 Architecture
- **Must Have**:
  - Single-machine deployment (no distributed complexity)
  - SQLite database for simplicity
  - REST API with OpenAPI documentation
  - Server-Sent Events for real-time updates
  - Stateless frontend with local storage

- **Should Have**:
  - Docker containerization option
  - Systemd service configuration
  - Backup and restore functionality
  - Health monitoring endpoints

#### 2.2 Integration Requirements
- **Must Have**:
  - OpenClaw agent spawning integration
  - Agent task execution tracking
  - Execution result capture and storage
  - Error handling and retry logic

- **Should Have**:
  - Webhook support for external triggers
  - API for programmatic access
  - Export/import functionality
  - Integration with existing agent team

### 3. User Experience Requirements

#### 3.1 Interface
- **Must Have**:
  - Clean, intuitive kanban interface
  - Responsive design (desktop/mobile)
  - Keyboard shortcuts
  - Search and filtering
  - Dark/light theme

- **Should Have**:
  - Customizable views
  - Advanced filtering
  - Keyboard navigation
  - Accessibility compliance

#### 3.2 Administration
- **Must Have**:
  - Agent configuration management
  - Workflow customization
  - System status dashboard
  - Log viewing

- **Should Have**:
  - User management (if multi-user)
  - Permission system
  - Audit logging
  - Performance analytics

---

## Success Criteria

### Phase 1: Core Functionality (Current Focus)
- [ ] Agents can receive tasks from the kanban system
- [ ] Agents can update task status during execution
- [ ] System detects and recovers from agent crashes
- [ ] Real-time updates work reliably
- [ ] Basic workflow (Backlog → Assigned → In Progress → Done) functions

### Phase 2: Enhanced Coordination
- [ ] Multiple agents can collaborate on complex tasks
- [ ] Task dependencies are respected
- [ ] Load balancing works effectively
- [ ] Performance metrics are tracked
- [ ] System handles concurrent agent execution

### Phase 3: Advanced Features
- [ ] External integrations (webhooks, APIs)
- [ ] Advanced workflow automation
- [ ] Comprehensive reporting
- [ ] Multi-project management
- [ ] Scalability improvements

---

## Technical Architecture

### System Components
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Mission       │    │   Database      │    │   Agent CLI     │
│   Control       │◄──►│   (SQLite →     │◄──►│   System        │
│   (Web UI)      │    │   PostgreSQL)   │    │                 │
│                 │    │                 │    │                 │
│ • Enhanced      │    │ • Tasks         │    │ • ren-agent     │
│   Kanban        │    │ • Agents        │    │ • aki-agent     │
│ • Agent Status  │    │ • Assignments   │    │ • kuro-agent    │
│ • Comments      │    │ • Results       │    │ • shin-agent    │
│ • Instructions  │    │ • Heartbeats    │    │ • sora-agent    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         ▲                                           ▲
         │                                           │
         └───────────────────┐                       │
                             │                       │
                     ┌─────────────────┐    ┌─────────────────┐
                     │   FastAPI       │    │   OpenClaw      │
                     │   Backend       │    │   Agents        │
                     │                 │    │                 │
                     │ • REST API      │    │ • Execution     │
                     │ • Real-time     │    │ • Results       │
                     │   updates       │    │ • Logging       │
                     │ • File locking  │    └─────────────────┘
                     │   for SQLite    │
                     └─────────────────┘
```

### Agent Assignment Logic
```
When task is created:
  IF task has assignee:
    → Wait for specific agent
    → Agent processes sequentially (finish current task first)
  ELSE:
    → Aki (main agent) grabs task immediately
    → Aki can assign to other agents if needed

Agent states:
  • Idle: Ready for work
  • Working: Processing task (can queue additional tasks)
  • Crashed: Detected failure, needs recovery
  • Offline: Not responding to heartbeats
```

### Heartbeat System Optimization
- **Local model only**: Use `qwen-coder-local` (GPU, no cost)
- **Minimal prompts**: Simple "ALIVE" check, no complex reasoning
- **Efficient scheduling**: Batch heartbeats to reduce model calls
- **Crash detection**: 2-minute timeout → automatic recovery

### Data Model
```sql
-- Core tables
Tasks (id, title, description, status, priority, assignee, created_at, updated_at)
Agents (id, name, role, status, last_heartbeat, capabilities)
Workflows (id, name, columns, transitions, rules)
AgentRuns (id, task_id, agent_id, status, started_at, completed_at, output, error)
```

### Integration Points
1. **OpenClaw Integration**: Spawn agents via CLI with task context
2. **Heartbeat System**: Regular status updates from agents
3. **Result Capture**: Store agent output and errors
4. **Crash Detection**: Timeout-based failure detection
5. **Recovery Logic**: Automatic retry or reassignment

---

## Current Gaps & Challenges

### 1. Integration Gap
**Problem**: The kanban system exists but agents cannot execute tasks from it.
**Root Cause**: Missing bridge between task assignment and agent execution.
**Solution**: Implement agent CLI integration that:
- Polls for assigned tasks
- Executes tasks via OpenClaw
- Updates task status
- Reports results back

### 2. Database Limitations
**Problem**: SQLite doesn't handle concurrent writes well for multiple agents.
**Root Cause**: Designed for single-writer scenarios.
**Solution**: Implement file-based locking for SQLite, design for PostgreSQL migration path.

### 3. Mission Control Requirement
**Problem**: Need comprehensive web interface for task management and agent monitoring.
**Root Cause**: Current frontend is basic kanban only.
**Solution**: Build Mission Control dashboard with:
- Enhanced kanban with drag & drop
- Agent status monitoring
- Task comments and instructions
- Real-time updates
- Administrative controls

### 2. Crash Recovery
**Problem**: Agent failures leave tasks stuck in "In Progress" state.
**Root Cause**: No heartbeat monitoring or automatic recovery.
**Solution**: Implement:
- Regular heartbeat checks
- Timeout-based failure detection
- Automatic task reassignment
- Failure logging and analysis

### 3. Real-time Sync
**Problem**: Multiple agents/clients see inconsistent states.
**Root Cause**: Polling-based updates cause delays.
**Solution**: Enhance with:
- Server-Sent Events for push updates
- Conflict resolution for concurrent edits
- State synchronization protocol

### 4. Workflow Complexity
**Problem**: Simple kanban doesn't capture AI agent workflow nuances.
**Root Cause**: Generic workflow vs. specialized agent needs.
**Solution**: Customize for:
- Agent-specific statuses (Planning, Code Review, Testing)
- Collaborative workflows (multiple agents on one task)
- Quality gates and review processes

---

## Roadmap

### Phase 1: CLI Foundation & Database (Today - Tomorrow)
- [ ] **Agent CLI System** (`agent-cli.py` + agent wrappers)
- [ ] **SQLite with file locking** for concurrent access
- [ ] **Task assignment logic** (specific agent vs Aki assignment)
- [ ] **Basic heartbeat system** using local qwen model
- [ ] **Test with Ren agent** first (simplest case)

### Phase 2: Mission Control Web UI (This Week)
- [ ] **Enhanced kanban** with drag & drop improvements
- [ ] **Agent status dashboard** (online/working/crashed)
- [ ] **Task comments and instructions** system
- [ ] **Real-time updates** via Server-Sent Events
- [ ] **Administrative controls** (start/stop agents, view logs)

### Phase 3: Advanced Features (Next Week)
- [ ] **Crash recovery automation** (detect & reassign tasks)
- [ ] **Performance metrics** and reporting
- [ ] **Workflow customization** (agent-specific statuses)
- [ ] **PostgreSQL migration** if SQLite becomes limiting
- [ ] **External integrations** (webhooks, API access)

### Phase 4: Production Readiness
- [ ] **Comprehensive testing** (unit, integration, end-to-end)
- [ ] **Performance optimization** (caching, query optimization)
- [ ] **Security hardening** (authentication, input validation)
- [ ] **Deployment automation** (Docker, systemd services)
- [ ] **User documentation** and training materials

---

## Risk Assessment

### High Risk
1. **Agent Integration Failure**: If agents cannot properly execute tasks, the system is useless.
   - **Mitigation**: Start with simple CLI integration, test extensively with Ren agent first.

2. **Real-time Sync Complexity**: Concurrent updates could cause data loss.
   - **Mitigation**: Implement optimistic locking, conflict resolution UI.

3. **Scalability Limitations**: SQLite may not handle high concurrency.
   - **Mitigation**: Design for eventual migration to PostgreSQL if needed.

### Medium Risk
1. **Workflow Over-engineering**: Adding too much complexity too quickly.
   - **Mitigation**: Start minimal, add features based on actual needs.

2. **UI/UX Challenges**: Creating an intuitive interface for complex workflows.
   - **Mitigation**: Iterative design, frequent user testing.

3. **Deployment Complexity**: Making it easy to install and maintain.
   - **Mitigation**: Provide Docker containers, systemd services, clear docs.

### Low Risk
1. **Feature Completeness**: Missing minor features.
   - **Mitigation**: Prioritize based on actual usage patterns.

2. **Performance Issues**: Slow response times.
   - **Mitigation**: Profile and optimize as needed.

---

## Metrics & Measurement

### Success Metrics
1. **Task Completion Rate**: % of tasks successfully completed by agents
2. **Agent Utilization**: % of time agents are actively working
3. **System Uptime**: % of time system is available and functional
4. **User Satisfaction**: Qualitative feedback from primary user
5. **Reduction in Manual Coordination**: Time saved on agent management

### Technical Metrics
1. **API Response Time**: < 100ms for 95% of requests
2. **Real-time Update Latency**: < 1 second for state changes
3. **Agent Heartbeat Interval**: Regular updates every 30 seconds
4. **Crash Detection Time**: < 2 minutes for agent failure detection
5. **Task Recovery Time**: < 5 minutes for automatic reassignment

---

## Conclusion

The custom kanban project represents a strategic pivot from complex external integrations to a simple, focused solution for AI agent orchestration. While significant progress has been made on the core kanban system, the critical integration bridge between task management and agent execution remains incomplete.

**Immediate Priority**: Implement the agent integration layer that allows Ren, Aki, Kuro, Shin, and Sora to receive tasks from the kanban, execute them via OpenClaw, and report results back. This is the missing piece that transforms a visualization tool into a functional orchestration system.

**Long-term Vision**: Create the definitive tool for AI agent team coordination—simple enough for solo practitioners, powerful enough for complex multi-agent workflows, and reliable enough for production use.

---

## Appendices

### Appendix A: Agent Team Configuration
```
Ren (ren-grunt): Infrastructure & maintenance (qwen-coder-local)
Aki (aki-partner): Coordination & reporting (deepseek/deepseek-chat)  
Kuro (kuro-coder): Technical execution (deepseek/deepseek-chat)
Shin (shin-strategist): Strategy & planning (deepseek/deepseek-chat)
Sora (sora-creative): Creative brainstorming (gemini)
```

### Appendix B: Related Documents
- `ARCHITECTURE.md` - Technical architecture details
- `API.md` - Complete REST API reference
- `AGENTS.md` - Agent integration guide
- `QUICKSTART.md` - Getting started guide
- `memory/2026-03-01.md` - Development history and context

### Appendix C: Glossary
- **Agent**: AI assistant (Ren, Aki, Kuro, Shin, Sora) capable of executing tasks
- **Orchestration**: Coordination of multiple agents to complete complex workflows
- **Heartbeat**: Regular status signal from agents to indicate they're alive
- **Crash Recovery**: Automatic detection and handling of agent failures
- **Kanban**: Visual workflow management system using columns and cards
- **OpenClaw**: The underlying platform running the AI agents