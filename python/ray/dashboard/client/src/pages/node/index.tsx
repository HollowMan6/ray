import {
  Box,
  Button,
  ButtonGroup,
  Grid,
  Link,
  Paper,
  Switch,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";
import Pagination from "@mui/material/Pagination";
import React from "react";
import { Outlet, Link as RouterLink } from "react-router-dom";
import { sliceToPage } from "../../common/util";
import Loading from "../../components/Loading";
import PercentageBar from "../../components/PercentageBar";
import { SearchInput, SearchSelect } from "../../components/SearchComponent";
import StateCounter from "../../components/StatesCounter";
import { StatusChip } from "../../components/StatusChip";
import TitleCard from "../../components/TitleCard";
import { HelpInfo } from "../../components/Tooltip";
import { NodeDetail } from "../../type/node";
import { memoryConverter } from "../../util/converter";
import { MainNavPageInfo } from "../layout/mainNavContext";
import { useNodeList } from "./hook/useNodeList";
import { NodeRows } from "./NodeRow";

const codeTextStyle = {
  fontFamily: "Roboto Mono, monospace",
};
const columns = [
  { label: "" }, // Expand button
  { label: "Host / Worker Process name" },
  { label: "State" },
  { label: "State Message" },
  { label: "ID" },
  { label: "IP / PID" },
  { label: "Actions" },
  {
    label: "CPU",
    helpInfo: (
      <Typography>
        Hardware CPU usage of a Node or a Worker Process.
        <br />
        <br />
        Node’s CPU usage is calculated against all CPU cores. Worker Process’s
        CPU usage is calculated against 1 CPU core. As a result, the sum of CPU
        usage from all Worker Processes is not equal to the Node’s CPU usage.
      </Typography>
    ),
  },
  {
    label: "Memory",
    helpInfo: (
      <Typography>
        A Node or a Worker Process's RAM usage. <br />
        <br />
        For a Node, Object Store holds up to 30% of RAM by default or a custom
        value configured by users.
        <br />
        <br />
        RAM is not pre-allocated for Object Store. Once memory is used by and
        allocated to Object Store, it will hold and not release it until the Ray
        Cluster is terminated.
      </Typography>
    ),
  },
  {
    label: "GPU",
    helpInfo: (
      <Typography>
        Usage of each GPU device. If no GPU usage is detected, here are the
        potential root causes:
        <br />
        1. non-GPU Ray image is used on this node. Switch to a GPU Ray image and
        try again. <br />
        2. Non Nvidia or AMD GPUs are being used.
        <br />
        3. pynvml or pyamdsmi module raises an exception.
      </Typography>
    ),
  },
  { label: "GRAM" },
  { label: "Object Store Memory" },
  {
    label: "Disk(root)",
    helpInfo:
      "For Ray Clusters on Kubernetes, multiple Ray Nodes/Pods may share the same Kubernetes Node's disk, resulting in multiple nodes having the same disk usage.",
  },
  { label: "Sent" },
  { label: "Received" },
  {
    label: "Logical Resources",
    helpInfo: (
      <Typography>
        <Link href="https://docs.ray.io/en/latest/ray-core/scheduling/resources.html#physical-resources-and-logical-resources">
          Logical resources usage
        </Link>{" "}
        (e.g., CPU, memory) for a node. Alternatively, you can run the CLI
        command <p style={codeTextStyle}>ray status -v </p>
        to obtain a similar result.
      </Typography>
    ),
  },
  { label: "Labels" },
];

export const brpcLinkChanger = (href: string) => {
  const { location } = window;
  const { pathname } = location;
  const pathArr = pathname.split("/");
  if (pathArr.some((e) => e.split(".").length > 1)) {
    const index = pathArr.findIndex((e) => e.includes("."));
    const resultArr = pathArr.slice(0, index);
    resultArr.push(href);
    return `${location.protocol}//${location.host}${resultArr.join("/")}`;
  }

  return `http://${href}`;
};

export const NodeCard = (props: { node: NodeDetail }) => {
  const { node } = props;

  if (!node) {
    return null;
  }

  const { raylet, hostname, ip, cpu, mem, networkSpeed, disk } = node;
  const { nodeId, state, objectStoreUsedMemory, objectStoreAvailableMemory } =
    raylet;

  const objectStoreTotalMemory =
    objectStoreUsedMemory + objectStoreAvailableMemory;

  return (
    <Paper variant="outlined" style={{ padding: "12px 12px", margin: 12 }}>
      <p style={{ fontWeight: "bold", fontSize: 12, textDecoration: "none" }}>
        <Link component={RouterLink} to={`nodes/${nodeId}`}>
          {nodeId}
        </Link>{" "}
      </p>
      <p>
        <Grid container spacing={1}>
          <Grid item>
            <StatusChip type="node" status={state} />
          </Grid>
          <Grid item>
            {hostname}({ip})
          </Grid>
          {networkSpeed && networkSpeed[0] >= 0 && (
            <Grid item>
              <span style={{ fontWeight: "bold" }}>Sent</span>{" "}
              {memoryConverter(networkSpeed[0])}/s{" "}
              <span style={{ fontWeight: "bold" }}>Received</span>{" "}
              {memoryConverter(networkSpeed[1])}/s
            </Grid>
          )}
        </Grid>
      </p>
      <Grid container spacing={1} alignItems="baseline">
        {cpu >= 0 && (
          <Grid item xs>
            CPU
            <PercentageBar num={Number(cpu)} total={100}>
              {cpu}%
            </PercentageBar>
          </Grid>
        )}
        {mem && (
          <Grid item xs>
            Memory
            <PercentageBar num={Number(mem[0] - mem[1])} total={mem[0]}>
              {memoryConverter(mem[0] - mem[1])}/{memoryConverter(mem[0])}(
              {mem[2]}%)
            </PercentageBar>
          </Grid>
        )}
        {raylet && (
          <Grid item xs>
            Object Store Memory
            <PercentageBar
              num={objectStoreUsedMemory}
              total={objectStoreTotalMemory}
            >
              {memoryConverter(objectStoreUsedMemory)}/
              {memoryConverter(objectStoreTotalMemory)}
            </PercentageBar>
          </Grid>
        )}
        {disk && disk["/"] && (
          <Grid item xs>
            Disk('/')
            <PercentageBar num={Number(disk["/"].used)} total={disk["/"].total}>
              {memoryConverter(disk["/"].used)}/
              {memoryConverter(disk["/"].total)}({disk["/"].percent}%)
            </PercentageBar>
          </Grid>
        )}
      </Grid>
      <Grid
        container
        justifyContent="flex-end"
        spacing={1}
        style={{ margin: 8 }}
      >
        <Grid>
          <Button>
            <Link
              component={RouterLink}
              to={`/logs/?nodeId${encodeURIComponent(raylet.nodeId)}`}
            >
              log
            </Link>
          </Button>
        </Grid>
      </Grid>
    </Paper>
  );
};

const Nodes = () => {
  const {
    msg,
    isLoading,
    isRefreshing,
    onSwitchChange,
    nodeList,
    changeFilter,
    page,
    setPage,
    setSortKey,
    setOrderDesc,
    mode,
    setMode,
  } = useNodeList();

  const {
    items: list,
    constrainedPage,
    maxPage,
  } = sliceToPage(nodeList, page.pageNo, page.pageSize);

  return (
    <Box
      sx={{
        padding: 2,
        width: "100%",
        position: "relative",
      }}
    >
      <Loading loading={isLoading} />
      <TitleCard title="NODES">
        Auto Refresh:
        <Switch
          checked={isRefreshing}
          onChange={onSwitchChange}
          name="refresh"
          inputProps={{ "aria-label": "secondary checkbox" }}
        />
        <br />
        Request Status: {msg}
      </TitleCard>
      <TitleCard title="Node Statistics">
        <StateCounter type="node" list={nodeList} />
      </TitleCard>
      <TitleCard title="Node List">
        <Grid container alignItems="center">
          <Grid item>
            <SearchInput
              label="Host"
              onChange={(value) => changeFilter("hostname", value.trim())}
            />
          </Grid>
          <Grid item>
            <SearchInput
              label="IP"
              onChange={(value) => changeFilter("ip", value.trim())}
            />
          </Grid>
          <Grid item>
            <SearchInput
              label="Node ID"
              onChange={(value) => changeFilter("nodeId", value.trim())}
            />
          </Grid>
          <Grid item>
            <SearchSelect
              label="State"
              onChange={(value) => changeFilter("state", value.trim())}
              options={["ALIVE", "DEAD"]}
              showAllOption={true}
            />
          </Grid>
          <Grid item>
            <SearchInput
              label="Page Size"
              onChange={(value) =>
                setPage("pageSize", Math.min(Number(value), 500) || 10)
              }
            />
          </Grid>
          <Grid item>
            <SearchSelect
              label="Sort By"
              options={[
                ["state", "State"],
                ["mem[2]", "Used Memory"],
                ["mem[0]", "Total Memory"],
                ["cpu", "CPU"],
                ["networkSpeed[0]", "Sent"],
                ["networkSpeed[1]", "Received"],
                ["disk./.used", "Used Disk"],
              ]}
              onChange={(val) => setSortKey(val)}
              showAllOption={true}
            />
          </Grid>
          <Grid item>
            <span style={{ margin: 8, marginTop: 0 }}>
              Reverse:
              <Switch onChange={(_, checked) => setOrderDesc(checked)} />
            </span>
          </Grid>
          <Grid item>
            <ButtonGroup size="small">
              <Button onClick={() => setMode("table")} color="primary">
                Table
              </Button>
              <Button onClick={() => setMode("card")} color="primary">
                Card
              </Button>
            </ButtonGroup>
          </Grid>
        </Grid>
        <div>
          <Pagination
            count={maxPage}
            page={constrainedPage}
            onChange={(e, pageNo) => setPage("pageNo", pageNo)}
          />
        </div>
        {mode === "table" && (
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  {columns.map(({ label, helpInfo }) => (
                    <TableCell align="center" key={label}>
                      <Box
                        display="flex"
                        justifyContent="center"
                        alignItems="center"
                      >
                        {label}
                        {helpInfo && (
                          <HelpInfo sx={{ marginLeft: 1 }}>{helpInfo}</HelpInfo>
                        )}
                      </Box>
                    </TableCell>
                  ))}
                </TableRow>
              </TableHead>
              <TableBody>
                {list.map((node) => (
                  <NodeRows
                    key={node.raylet.nodeId}
                    node={node}
                    isRefreshing={isRefreshing}
                    startExpanded={nodeList.length === 1}
                  />
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        )}
        {mode === "card" && (
          <Grid container>
            {list.map((e) => (
              <Grid item xs={6}>
                <NodeCard node={e} />
              </Grid>
            ))}
          </Grid>
        )}
      </TitleCard>
    </Box>
  );
};

/**
 * Cluster page for the new IA
 */
export const ClusterMainPageLayout = () => {
  return (
    <React.Fragment>
      <MainNavPageInfo
        pageInfo={{
          title: "Cluster",
          id: "cluster",
          path: "/cluster",
        }}
      />
      <Outlet />
    </React.Fragment>
  );
};

export default Nodes;
