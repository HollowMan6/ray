// Copyright 2024 The Ray Authors.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//  http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

#pragma once

#include <memory>
#include <string>

#include "ray/gcs/gcs_server/gcs_kv_manager.h"
#include "src/ray/protobuf/usage.pb.h"

namespace ray {
namespace gcs {
class UsageStatsClient {
 public:
  explicit UsageStatsClient(ray::gcs::InternalKVInterface &internal_kv,
                            instrumented_io_context &io_context);

  /// C++ version of record_extra_usage_tag in usage_lib.py
  ///
  /// \param key The tag key which MUST be a registered TagKey in usage_lib.py.
  /// \param value The tag value.
  void RecordExtraUsageTag(usage::TagKey key, const std::string &value);

  // Report a monotonically increasing counter.
  void RecordExtraUsageCounter(usage::TagKey key, int64_t counter);

 private:
  /// Kee in-sync with the same constants defined in usage_constants.py
  static constexpr char kExtraUsageTagPrefix[] = "extra_usage_tag_";
  static constexpr char kUsageStatsNamespace[] = "usage_stats";

  ray::gcs::InternalKVInterface &internal_kv_;
  instrumented_io_context &io_context_;
};
}  // namespace gcs
}  // namespace ray
