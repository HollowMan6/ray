load("//bazel:ray.bzl", "ray_cc_library", "ray_cc_test")

ray_cc_test(
    name = "cgroup_v2_utils_privileged_test",
    size = "small",
    srcs = ["cgroup_v2_utils_privileged_test.cc"],
    tags = [
        "cgroup",
        "exclusive",
        "no_windows",
        "team:core",
    ],
    deps = [
        "//src/ray/common/cgroup:cgroup_setup",
        "//src/ray/common/test:testing",
        "@com_google_googletest//:gtest_main",
    ],
)

ray_cc_test(
    name = "cgroup_v2_utils_unprivileged_test",
    size = "small",
    srcs = ["cgroup_v2_utils_unprivileged_test.cc"],
    tags = [
        "exclusive",
        "team:core",
    ],
    deps = [
        "//src/ray/common/cgroup:cgroup_setup",
        "//src/ray/common/test:testing",
        "@com_google_googletest//:gtest_main",
    ],
)

ray_cc_test(
    name = "fake_cgroup_setup_test",
    srcs = ["fake_cgroup_setup_test.cc"],
    tags = [
        "team:core",
    ],
    deps = [
        "//src/ray/common/cgroup:fake_cgroup_setup",
        "//src/ray/common/test:testing",
        "@com_google_googletest//:gtest_main",
    ],
)

ray_cc_test(
    name = "cgroup_v2_setup_test",
    srcs = ["cgroup_v2_setup_test.cc"],
    tags = [
        "cgroup",
        "team:core",
    ],
    deps = [
        ":cgroup_test_utils",
        "//src/ray/common/cgroup:cgroup_setup",
        "//src/ray/common/cgroup:cgroup_utils",
        "//src/ray/common/test:testing",
        "@com_google_googletest//:gtest_main",
    ],
)

ray_cc_library(
    name = "cgroup_test_utils",
    testonly = True,
    srcs = ["cgroup_test_utils.cc"],
    hdrs = ["cgroup_test_utils.h"],
    deps = [
        "//src/ray/common/test:testing",
        "//src/ray/util:compat",
        "//src/ray/util:container_util",
        "//src/ray/util:filesystem",
        "@com_google_absl//absl/strings",
        "@com_google_googletest//:gtest",
    ],
)
