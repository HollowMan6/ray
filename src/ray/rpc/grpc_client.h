// Copyright 2017 The Ray Authors.
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

#include <grpcpp/grpcpp.h>

#include <boost/asio.hpp>
#include <memory>
#include <string>
#include <utility>

#include "ray/common/grpc_util.h"
#include "ray/common/ray_config.h"
#include "ray/common/status.h"
#include "ray/rpc/client_call.h"
#include "ray/rpc/common.h"
#include "ray/rpc/rpc_chaos.h"

namespace ray {
namespace rpc {

// This macro wraps the logic to call a specific RPC method of a service,
// to make it easier to implement a new RPC client.
#define INVOKE_RPC_CALL(                                               \
    SERVICE, METHOD, request, callback, rpc_client, method_timeout_ms) \
  (rpc_client->CallMethod<METHOD##Request, METHOD##Reply>(             \
      &SERVICE::Stub::PrepareAsync##METHOD,                            \
      request,                                                         \
      callback,                                                        \
      #SERVICE ".grpc_client." #METHOD,                                \
      method_timeout_ms))

// Define a void RPC client method declaration
#define VOID_RPC_CLIENT_VIRTUAL_METHOD_DECL(SERVICE, METHOD) \
  virtual void METHOD(const METHOD##Request &request,        \
                      const ClientCallback<METHOD##Reply> &callback) = 0;

// Define a void RPC client method.
#define VOID_RPC_CLIENT_METHOD(SERVICE, METHOD, rpc_client, method_timeout_ms, SPECS)   \
  void METHOD(const METHOD##Request &request,                                           \
              const ClientCallback<METHOD##Reply> &callback) SPECS {                    \
    INVOKE_RPC_CALL(SERVICE, METHOD, request, callback, rpc_client, method_timeout_ms); \
  }

inline std::shared_ptr<grpc::Channel> BuildChannel(
    const std::string &address,
    int port,
    std::optional<grpc::ChannelArguments> arguments = std::nullopt) {
  if (!arguments.has_value()) {
    arguments = grpc::ChannelArguments();
  }

  arguments->SetInt(GRPC_ARG_ENABLE_HTTP_PROXY,
                    ::RayConfig::instance().grpc_enable_http_proxy() ? 1 : 0);
  arguments->SetMaxSendMessageSize(::RayConfig::instance().max_grpc_message_size());
  arguments->SetMaxReceiveMessageSize(::RayConfig::instance().max_grpc_message_size());
  arguments->SetInt(GRPC_ARG_HTTP2_WRITE_BUFFER_SIZE,
                    ::RayConfig::instance().grpc_stream_buffer_size());
  std::shared_ptr<grpc::Channel> channel;
  if (::RayConfig::instance().USE_TLS()) {
    std::string server_cert_file = std::string(::RayConfig::instance().TLS_SERVER_CERT());
    std::string server_key_file = std::string(::RayConfig::instance().TLS_SERVER_KEY());
    std::string root_cert_file = std::string(::RayConfig::instance().TLS_CA_CERT());
    std::string server_cert_chain = ReadCert(server_cert_file);
    std::string private_key = ReadCert(server_key_file);
    std::string cacert = ReadCert(root_cert_file);

    grpc::SslCredentialsOptions ssl_opts;
    ssl_opts.pem_root_certs = cacert;
    ssl_opts.pem_private_key = private_key;
    ssl_opts.pem_cert_chain = server_cert_chain;
    auto ssl_creds = grpc::SslCredentials(ssl_opts);
    channel = grpc::CreateCustomChannel(
        address + ":" + std::to_string(port), ssl_creds, *arguments);
  } else {
    channel = grpc::CreateCustomChannel(address + ":" + std::to_string(port),
                                        grpc::InsecureChannelCredentials(),
                                        *arguments);
  }
  return channel;
}

template <class GrpcService>
class GrpcClient {
 public:
  GrpcClient(std::shared_ptr<grpc::Channel> channel,
             ClientCallManager &call_manager,
             bool use_tls = false)
      : client_call_manager_(call_manager),
        channel_(std::move(channel)),
        stub_(GrpcService::NewStub(channel_)),
        use_tls_(use_tls) {}

  GrpcClient(const std::string &address,
             const int port,
             ClientCallManager &call_manager,
             bool use_tls = false,
             grpc::ChannelArguments channel_arguments = CreateDefaultChannelArguments())
      : client_call_manager_(call_manager),
        channel_(BuildChannel(address, port, std::move(channel_arguments))),
        stub_(GrpcService::NewStub(channel_)),
        use_tls_(use_tls) {}

  /// Create a new `ClientCall` and send request.
  ///
  /// \tparam Request Type of the request message.
  /// \tparam Reply Type of the reply message.
  ///
  /// \param[in] prepare_async_function Pointer to the gRPC-generated
  /// `FooService::Stub::PrepareAsyncBar` function.
  /// \param[in] request The request message.
  /// \param[in] callback The callback function that handles reply.
  /// \param[in] call_name The name of the gRPC method call.
  /// \param[in] method_timeout_ms The timeout of the RPC method in ms.
  /// -1 means it will use the default timeout configured for the handler.
  ///
  /// \return Status.
  template <class Request, class Reply>
  void CallMethod(
      const PrepareAsyncFunction<GrpcService, Request, Reply> prepare_async_function,
      const Request &request,
      const ClientCallback<Reply> &callback,
      std::string call_name = "UNKNOWN_RPC",
      int64_t method_timeout_ms = -1) {
    testing::RpcFailure failure = testing::GetRpcFailure(call_name);
    if (failure == testing::RpcFailure::Request) {
      // Simulate the case where the PRC fails before server receives
      // the request.
      RAY_LOG(INFO) << "Inject RPC request failure for " << call_name;
      client_call_manager_.GetMainService().post(
          [callback]() {
            callback(Status::RpcError("Unavailable", grpc::StatusCode::UNAVAILABLE),
                     Reply());
          },
          "RpcChaos");
    } else if (failure == testing::RpcFailure::Response) {
      // Simulate the case where the RPC fails after server sends
      // the response.
      RAY_LOG(INFO) << "Inject RPC response failure for " << call_name;
      client_call_manager_.CreateCall<GrpcService, Request, Reply>(
          *stub_,
          prepare_async_function,
          request,
          [callback](const Status &status, const Reply &) {
            callback(Status::RpcError("Unavailable", grpc::StatusCode::UNAVAILABLE),
                     Reply());
          },
          std::move(call_name),
          method_timeout_ms);
    } else {
      auto call = client_call_manager_.CreateCall<GrpcService, Request, Reply>(
          *stub_,
          prepare_async_function,
          request,
          callback,
          std::move(call_name),
          method_timeout_ms);
      RAY_CHECK(call != nullptr);
    }

    call_method_invoked_.store(true);
  }

  std::shared_ptr<grpc::Channel> Channel() const { return channel_; }

  /// A channel is IDLE when it's first created before making any RPCs
  /// or after GRPC_ARG_CLIENT_IDLE_TIMEOUT_MS of no activities since the last RPC.
  /// This method detects IDLE in the second case.
  /// Also see https://grpc.github.io/grpc/core/md_doc_connectivity-semantics-and-api.html
  /// for channel connectivity state machine.
  bool IsChannelIdleAfterRPCs() const {
    return (channel_->GetState(false) == GRPC_CHANNEL_IDLE) &&
           call_method_invoked_.load();
  }

 private:
  ClientCallManager &client_call_manager_;
  /// The channel of the stub.
  std::shared_ptr<grpc::Channel> channel_;
  /// The gRPC-generated stub.
  std::unique_ptr<typename GrpcService::Stub> stub_;
  /// Whether CallMethod is invoked.
  std::atomic<bool> call_method_invoked_ = false;
  /// Whether to use TLS.
  bool use_tls_;
};

}  // namespace rpc
}  // namespace ray
