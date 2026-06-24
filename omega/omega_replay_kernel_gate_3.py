from omega_kernel_freeze_guard import assert_kernel_frozen

def run_replay():
    assert_kernel_frozen("build_postings_from_events_kernel_v9_fixed.py")
    assert_kernel_frozen("invariant_engine_kernel_v4.py")
    assert_kernel_frozen("omega_replay_runtime_v1_fixed.py")
