#include <assert.h>
#include <math.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "motion.h"
#include "homing.h"
#include "hal.h"
#include "simple_tp.h"

/* A HAL allocation seam; tests use the public pins and HOMEMOD API. */
static hal_bit_t *home_inputs[EMCMOT_MAX_JOINTS];
static hal_s32_t *home_states[EMCMOT_MAX_JOINTS];
void *hal_malloc(long size) { return calloc(1, size); }
int hal_pin_bit_newf(hal_pin_dir_t dir, hal_bit_t **ptr, int id, const char *fmt, ...) {
    (void)dir; (void)id;
    *ptr = calloc(1, sizeof(**ptr));
    va_list ap; va_start(ap, fmt); int joint = va_arg(ap, int); va_end(ap);
    if (strstr(fmt, "home-sw-in")) home_inputs[joint] = *ptr;
    return 0;
}
int hal_pin_s32_newf(hal_pin_dir_t dir, hal_s32_t **ptr, int id, const char *fmt, ...) {
    (void)dir; (void)id;
    *ptr = calloc(1, sizeof(**ptr));
    va_list ap; va_start(ap, fmt); int joint = va_arg(ap, int); va_end(ap);
    home_states[joint] = *ptr;
    return 0;
}
void rtapi_print_msg(msg_level_t level, const char *fmt, ...) {
    (void)level;
    va_list ap; va_start(ap, fmt); vfprintf(stderr, fmt, ap); va_end(ap);
}

int main(int argc, char **argv) {
    assert(argc == 3);
    const char *mode = argv[1];
    const int axis = atoi(argv[2]);
    const double direction = axis == 1 ? 1 : -1;
    const double retreat = 5;
    const double dt = 0.001;
    emcmot_joint_t plant[3] = {0};
    assert(homing_init(0, dt, 3, 0, plant) == 0);
    emcmot_joint_t *j = &plant[axis];
    j->flag = EMCMOT_JOINT_ACTIVE_BIT;
    j->vel_limit = 10;
    j->min_pos_limit = -30;
    j->max_pos_limit = 30;
    j->free_tp.max_acc = 100;
    double physical = !strcmp(mode, "initially-active") ? direction * 0.2 : -direction * 10;
    j->pos_cmd = j->pos_fb = j->free_tp.curr_pos = physical;
    set_joint_homing_params(axis, direction * retreat, 0, 2,
                           !strcmp(mode, "wrong-direction") ? -direction * 2 : direction * 2,
                           direction * 0.5, HOME_IGNORE_LIMITS, axis + 1, 0);
    do_home_joint(axis);
    int touches = 0, previous_switch = 0, cancelled = 0, ticks = 0;
    double first_retreat = -1;
    for (; ticks < 160000; ticks++) {
        int sw = physical * direction >= 0;
        if (!strcmp(mode, "missing")) sw = 0;
        if (!strcmp(mode, "stuck") && touches >= 1) sw = 1;
        if (!strcmp(mode, "final-stuck") && touches >= 2) sw = 1;
        if (sw && !previous_switch) touches++;
        previous_switch = sw;
        *home_inputs[axis] = sw;
        if (axis == 1) j->on_pos_limit = sw;
        else j->on_neg_limit = sw;
        read_homing_in_pins(3);
        if ((!strcmp(mode, "cancel") && ticks == 1000)
            || (!strcmp(mode, "cancel-retreat") && *home_states[axis] == 10)) {
            do_cancel_homing(axis);
            cancelled = 1;
        }
        if (!strcmp(mode, "limit") && ticks == 1000) {
            if (axis == 1) j->on_neg_limit = 1;
            else j->on_pos_limit = 1;
        }
        do_homing();
        write_homing_out_pins(3);
        if (*home_states[axis] == 11 && first_retreat < 0)
            first_retreat = -direction * physical;
        double before = j->free_tp.curr_pos;
        simple_tp_update(&j->free_tp, dt);
        physical += j->free_tp.curr_pos - before;
        j->pos_cmd = j->pos_fb = j->free_tp.curr_pos;
        if (ticks > 1 && get_home_is_idle(axis) && !j->free_tp.active) break;
    }
    assert(ticks < 160000);
    if (!strcmp(mode, "normal") || !strcmp(mode, "initially-active")) {
        assert(get_homed(axis));
        assert(touches == (!strcmp(mode, "initially-active") ? 3 : 2));
        assert(fabs(first_retreat - retreat) < 0.005);
        assert(fabs(physical + direction * retreat) < 0.005);
        assert(fabs(j->pos_fb) < 0.005);
    } else {
        assert(!get_homed(axis));
        assert(!j->free_tp.enable);
        if (!strcmp(mode, "cancel")) assert(cancelled && ticks < 2000);
        if (!strcmp(mode, "cancel-retreat")) assert(cancelled);
        if (!strcmp(mode, "stuck")) assert(first_retreat < 0);
    }
    printf("%s axis=%d touches=%d final=%.4f first-retreat=%.4f passed\n",
           mode, axis, touches, physical, first_retreat);
    return 0;
}
