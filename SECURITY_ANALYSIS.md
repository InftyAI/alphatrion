# Security Analysis: SQL Access Control Vulnerabilities

## Executive Summary

Analysis Date: 2026-05-26
Analyzed File: `alphatrion/storage/sqlstore.py`
Status: **1 CRITICAL BUG FOUND** + Several potential vulnerabilities identified

---

## 🚨 CRITICAL: Bug in `dataset_is_accessible_to_user`

### Location
File: `alphatrion/storage/sqlstore.py`
Lines: 1496-1523

### The Bug
```python
def dataset_is_accessible_to_user(
    self, dataset_id: uuid.UUID, user_id: uuid.UUID
) -> bool:
    session = self._session()
    dst = (
        session.query(Dataset)
        .filter(Dataset.uuid == dataset_id, Agent.is_del == 0)  # ← BUG HERE!
        .first()
    )
```

**Problem**: The query filters by `Agent.is_del == 0` instead of `Dataset.is_del == 0`

**Impact**: 
- This will cause a SQL error or unexpected behavior
- Deleted datasets may still be accessible
- Query might fail completely

**Fix**:
```python
.filter(Dataset.uuid == dataset_id, Dataset.is_del == 0)  # Correct
```

---

## 🔍 Security Vulnerability Analysis

### 1. ✅ `user_is_super_admin_in_org` - SECURE

**Query Pattern**:
```python
session.query(TeamMember)
    .filter(
        TeamMember.user_id == user_id,
        TeamMember.org_id == org_id,
        TeamMember.role == MemberRole.SUPER_ADMIN,
    )
```

**Security Assessment**: ✅ SAFE
- Checks all three required fields
- No cross-org privilege escalation possible
- Properly validates org membership

---

### 2. ⚠️ `team_is_accessible_to_user` - POTENTIAL ISSUE

**Query Pattern**:
```python
# First get team (no org check!)
team = self.get_team(team_id)

# Then check super admin
if self.user_is_super_admin_in_org(user_id, team.org_id):
    return True

# Or check team membership
membership = session.query(TeamMember).filter(
    TeamMember.team_id == team_id,
    TeamMember.user_id == user_id,
).first()
```

**Potential Vulnerability**:
```python
def get_team(self, team_id):
    # Returns team WITHOUT checking if user's org matches!
    return session.query(Team).filter(Team.uuid == team_id).first()
```

**Attack Scenario**:
1. Attacker is user in Org A
2. Target team is in Org B  
3. `get_team()` returns Team B (no org filter!)
4. Super admin check: `user_is_super_admin_in_org(user_A, org_B)` → False ✅
5. Team membership check: `TeamMember.team_id == team_B AND user_id == user_A` → False ✅

**Conclusion**: ✅ SAFE - Both checks will fail, but inefficient

**Recommendation**: Add org validation early:
```python
def team_is_accessible_to_user(self, team_id, user_id):
    team = self.get_team(team_id)
    if team is None:
        return False
    
    # Get user's org
    user = self.get_user(user_id)
    if user is None or user.org_id != team.org_id:
        return False  # Different orgs
    
    # Now check permissions
    ...
```

---

### 3. ✅ `org_is_accessible_to_user` - SECURE

**Query Pattern**:
```python
session.query(User).filter(
    User.uuid == user_id,
    User.org_id == org_id,
    User.is_del == 0
)
```

**Security Assessment**: ✅ SAFE
- Directly validates user belongs to org
- Checks soft delete flag
- No bypass possible

---

### 4. ✅ `user_and_team_in_same_org` - SECURE

**Query Pattern**:
```python
# Step 1: Get team
team = query(Team).filter(Team.uuid == team_id, Team.is_del == 0)

# Step 2: Verify team in target org
if team.org_id != target_org_id:
    return False

# Step 3: Verify user in team's org
user = query(User).filter(
    User.uuid == user_id,
    User.org_id == team.org_id,  # ← Key security check
    User.is_del == 0
)
```

**Security Assessment**: ✅ SAFE
- Transitive check ensures: `user.org_id == team.org_id == target_org_id`
- Cannot bypass with cross-org IDs
- Properly validates all relationships

---

### 5. ⚠️ `experiment_is_accessible_to_user` - MISSING ORG CHECK

**Query Pattern**:
```python
# Step 1: Get experiment (no org validation!)
exp = session.query(Experiment).filter(
    Experiment.uuid == experiment_id,
    Experiment.is_del == 0
).first()

# Step 2: Check if super admin in exp's org
if self.user_is_super_admin_in_org(user_id, exp.org_id):
    return True

# Step 3: Check team membership
membership = session.query(TeamMember).filter(
    TeamMember.team_id == exp.team_id,
    TeamMember.user_id == user_id,
).first()
```

**Potential Vulnerability**: 
The team membership check does NOT verify the user is in the same org!

**Attack Scenario**:
```
Org A:
  - User Alice (user_id: alice_id)
  - Team X (team_id: team_x)

Org B:
  - User Bob (user_id: bob_id) 
  - Team Y (team_id: team_y)
  - Experiment Z (exp_id: exp_z, team_id: team_y)

Attack:
1. Bob creates TeamMember(user_id=alice_id, team_id=team_y)
2. Alice calls get_experiment(exp_z)
3. Check: user_is_super_admin_in_org(alice_id, org_b) → False ✅
4. Check: TeamMember where team_id=team_y AND user_id=alice_id → FOUND! ❌
5. Alice can access Org B's experiment!
```

**Root Cause**: `TeamMember` table doesn't enforce org consistency in the query!

**Critical Check Required**: Does `TeamMember` table have an `org_id` column?

Let me check:

---

### 6. Similar Issues in Other Methods

The same pattern appears in:
- `run_is_accessible_to_user` (line 1415)
- `agent_is_accessible_to_user` (line 1438)
- `session_is_accessible_to_user` (line 1467)  
- `dataset_is_accessible_to_user` (line 1496)

All use the same vulnerable pattern:
```python
membership = session.query(TeamMember).filter(
    TeamMember.team_id == resource.team_id,
    TeamMember.user_id == user_id,
    # ← MISSING: TeamMember.org_id == resource.org_id
).first()
```

---

## 🎯 Recommended Fixes

### Fix 1: Verify TeamMember Schema

Check if `TeamMember` table has `org_id` column:
```python
class TeamMember(Base):
    user_id = Column(...)
    team_id = Column(...)
    org_id = Column(...)  # ← Does this exist?
```

**If YES**: Update all queries to include org check:
```python
membership = session.query(TeamMember).filter(
    TeamMember.team_id == resource.team_id,
    TeamMember.user_id == user_id,
    TeamMember.org_id == resource.org_id,  # ← ADD THIS
).first()
```

**If NO**: Add foreign key constraint or join with User table:
```python
membership = (
    session.query(TeamMember)
    .join(User, User.uuid == TeamMember.user_id)
    .filter(
        TeamMember.team_id == resource.team_id,
        TeamMember.user_id == user_id,
        User.org_id == resource.org_id,  # ← Verify via User
    )
    .first()
)
```

### Fix 2: Critical Bug in dataset_is_accessible_to_user

```python
# Line 1502 - Change from:
.filter(Dataset.uuid == dataset_id, Agent.is_del == 0)

# To:
.filter(Dataset.uuid == dataset_id, Dataset.is_del == 0)
```

### Fix 3: Add Integration Tests

Test cross-org attack scenarios:
1. User in Org A tries to access resource in Org B
2. Malicious admin adds cross-org team membership
3. Verify all `*_is_accessible_to_user` methods reject

---

## 🔒 Security Best Practices Violations

1. **Lack of Defense in Depth**: Single point of failure if TeamMember table is corrupted
2. **Missing Org Validation**: Many methods don't validate org_id in JOIN queries
3. **Inconsistent Patterns**: `org_is_accessible_to_user` validates org directly, but others rely on team membership
4. **No Audit Logging**: Access control checks don't log failed attempts

---

## ✅ What IS Secure

1. Super admin checks properly validate org_id
2. User-to-org relationships are validated
3. Soft delete flags are consistently checked
4. UUID-based lookups prevent SQL injection
5. `user_and_team_in_same_org` has correct transitive validation

---

## 📊 Risk Assessment

| Vulnerability | Severity | Exploitable? | Fix Priority |
|---------------|----------|--------------|--------------|
| dataset_is_accessible bug | HIGH | YES | CRITICAL |
| Missing org check in TeamMember queries | HIGH | Depends on schema | HIGH |
| Inefficient team lookup | LOW | NO | MEDIUM |
| No audit logging | MEDIUM | N/A | LOW |

---

## 🎬 Action Items

1. **IMMEDIATE**: Fix `dataset_is_accessible_to_user` bug (line 1502)
2. **URGENT**: Verify TeamMember table schema for org_id column
3. **HIGH**: Add org_id validation to all TeamMember queries if column exists
4. **MEDIUM**: Add integration tests for cross-org attacks
5. **LOW**: Add audit logging for failed access attempts

---

## Next Steps

Need to check:
1. TeamMember table schema definition
2. Whether cross-org team memberships are possible
3. Database constraints preventing invalid memberships
