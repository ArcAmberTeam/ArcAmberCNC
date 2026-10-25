/* Reuse only the test's HAL allocation seam, never private HOMEMOD state. */
#define main single_axis_harness_main
#include "test_homing.c"
#undef main

int main(int argc, char **argv) {
    assert(argc == 3);
    const char *mode = argv[1];
    const int fault = atoi(argv[2]);
    const double dt = .001;
    emcmot_joint_t plant[3] = {0};
    double physical[3], overtravel[3] = {0}, retreat_peak[3] = {0};
    double search_peak[3] = {0}, latch_peak[3] = {0};
    int delay[3][5] = {{0}}, previous[3] = {0}, touches[3] = {0};
    int finished_before_failure = 0, cancelled = 0, ticks;
    assert(homing_init(0, dt, 3, 0, plant) == 0);
    for (int axis = 0; axis < 3; axis++) {
        emcmot_joint_t *j = &plant[axis];
        j->flag = EMCMOT_JOINT_ACTIVE_BIT;
        j->vel_limit = 25;
        j->min_pos_limit = -.1;
        j->max_pos_limit = axis == 0 ? 410 : axis == 1 ? 265 : 80;
        j->free_tp.max_acc = 750;
        physical[axis] = !strcmp(mode, "initially-active") ? -.2 : 10 + axis;
        j->pos_cmd = j->pos_fb = j->free_tp.curr_pos = physical[axis];
        *backoff_inputs[axis] = 2;
        if (!strcmp(mode, "invalid-backoff") && axis == fault)
            *backoff_inputs[axis] = NAN;
        set_joint_homing_params(axis, -5, 0, axis == 2 ? 2 : 5,
                                axis == 2 ? -5 : -15, -1, HOME_IGNORE_LIMITS, 1, 0);
        for (int sample = 0; sample < 5; sample++)
            delay[axis][sample] = physical[axis] <= 0;
    }
    do_home_joint(-1);
    for (ticks = 0; ticks < 250000; ticks++) {
        for (int axis = 0; axis < 3; axis++) {
            int raw = physical[axis] <= 0;
            if (axis == fault) {
                if (!strcmp(mode, "missing")) raw = 0;
                if (!strcmp(mode, "stuck") && touches[axis] >= 1) raw = 1;
                if (!strcmp(mode, "final-stuck") && touches[axis] >= 2) raw = 1;
            }
            /* Five complete servo periods of sensor/debounce delay. */
            int sw = delay[axis][ticks % 5];
            delay[axis][ticks % 5] = raw;
            if (sw && !previous[axis]) touches[axis]++;
            previous[axis] = sw;
            *home_inputs[axis] = sw;
            plant[axis].on_neg_limit = sw;
            if (get_homed(axis)) finished_before_failure = 1;
        }
        read_homing_in_pins(3);
        if ((!strcmp(mode, "cancel") && ticks == 1000)
            || (!strcmp(mode, "cancel-retreat") && *home_states[fault] == 10)) {
            do_cancel_homing(fault);
            cancelled = 1;
        }
        if (!strcmp(mode, "limit") && ticks == 1000)
            plant[fault].on_pos_limit = 1;
        do_homing();
        write_homing_out_pins(3);
        int idle = 1;
        for (int axis = 0; axis < 3; axis++) {
            emcmot_joint_t *j = &plant[axis];
            double before = j->free_tp.curr_pos;
            simple_tp_update(&j->free_tp, dt);
            double velocity = (j->free_tp.curr_pos - before) / dt;
            physical[axis] += j->free_tp.curr_pos - before;
            j->pos_cmd = j->pos_fb = j->free_tp.curr_pos;
            overtravel[axis] = fmax(overtravel[axis], -physical[axis]);
            if (*home_states[axis] == 10 && velocity > 0)
                retreat_peak[axis] = fmax(retreat_peak[axis], velocity);
            if (*home_states[axis] == 7)
                search_peak[axis] = fmax(search_peak[axis], -velocity);
            if (*home_states[axis] == 12)
                latch_peak[axis] = fmax(latch_peak[axis], -velocity);
            idle &= get_home_is_idle(axis) && !j->free_tp.active;
        }
        if (ticks > 4 && idle) break;
    }
    assert(ticks < 250000);
    int success = !strcmp(mode, "normal") || !strcmp(mode, "initially-active");
    for (int axis = 0; axis < 3; axis++) {
        if (success) {
            assert(get_homed(axis));
            assert(touches[axis] == (!strcmp(mode, "initially-active") ? 3 : 2));
            double search_limit = axis == 2 ? 5 : 15;
            assert(search_peak[axis] > 0 && search_peak[axis] <= search_limit + .001);
            /* A switch already pressed at start clears only a short distance;
               the next approach must not require reaching full cruise speed. */
            if (!strcmp(mode, "normal"))
                assert(fabs(search_peak[axis] - search_limit) < .001);
            assert(fabs(retreat_peak[axis] - 2) < .001);
            assert(fabs(latch_peak[axis] - 1) < .001);
            assert(overtravel[axis] < .5);
            assert(fabs(physical[axis] - 5) < .02);
            assert(plant[axis].pos_fb >= plant[axis].min_pos_limit);
            assert(fabs(plant[axis].pos_fb) < .001);
        } else {
            assert(!get_homed(axis));
            assert(!plant[axis].free_tp.enable);
        }
        printf("parallel %s fault=%d axis=%d overtravel=%.6f mm retreat=%.3f mm/s passed\n",
               mode, fault, axis, overtravel[axis], retreat_peak[axis]);
    }
    if (!strcmp(mode, "missing")) assert(finished_before_failure);
    if (!strncmp(mode, "cancel", 6)) assert(cancelled);
    return 0;
}
