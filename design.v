// ProbeDriver2: Voltage-triggered dual-output pulse generator
// Platform: Moku:Go (31.25 MHz clock, 16-bit signed I/O)
// Pipeline latency: 1 cycle (threshold comparison to state transition)
//
// FSM States:
//   S_RESET (0x00): Latch parameters, transition to S_IDLE
//   S_IDLE  (0x01): Monitor inputa for threshold crossing
//   S_FIRE  (0x02): Drive outputs for 'duration' cycles
//   S_COOL  (0x03): Zero outputs for 'duration*2' cycles
//   S_FINI  (0x04): Hold zero outputs until RESET
//
// Control registers:
//   control[0][31]   - ARM: Output enable
//   control[0][30]   - RESET: High-to-low edge triggers parameter latch
//   control[1][15:0] - trigger_out_v: Output A voltage during Fire
//   control[2][15:0] - intensity_out_v: Output B voltage during Fire
//   control[3][15:0] - threshold_v: Trigger threshold (signed)
//   control[4][15:0] - duration: Fire duration in clock cycles
//
// Status registers:
//   status[0][4:0] - Current FSM state encoding

/* verilator lint_off UNUSEDSIGNAL */

module CustomInstrument (
    input wire clk,
    input wire reset,
    input wire [31:0] sync,

    input wire signed [15:0] inputa,
    input wire signed [15:0] inputb,
    input wire signed [15:0] inputc,
    input wire signed [15:0] inputd,

    input wire exttrig,

    output wire signed [15:0] outputa,
    output wire signed [15:0] outputb,
    output wire signed [15:0] outputc,
    output wire signed [15:0] outputd,

    input wire [31:0] control [0:15],
    output wire [31:0] status [0:15]
);

  //==========================================================================
  // Type Definitions and Parameters
  //==========================================================================

  // FSM state encoding
  localparam logic [4:0] S_RESET = 5'h00;
  localparam logic [4:0] S_IDLE  = 5'h01;
  localparam logic [4:0] S_FIRE  = 5'h02;
  localparam logic [4:0] S_COOL  = 5'h03;
  localparam logic [4:0] S_FINI  = 5'h04;

  //==========================================================================
  // Signal Declarations
  //==========================================================================

  // Control signal extraction (continuous read)
  wire        arm_w;
  wire        reset_cmd_w;

  // RESET edge detection
  logic       reset_cmd_prev_r;
  wire        reset_edge_w;

  // Latched parameters (captured on RESET edge)
  logic signed [15:0] trigger_out_v_r;
  logic signed [15:0] intensity_out_v_r;
  logic signed [15:0] threshold_v_r;
  logic        [15:0] duration_r;

  // FSM state register
  logic [4:0] state_r;

  // Cycle counter (17-bit for cooldown = duration*2)
  logic [16:0] cycle_count_r;

  // Cooldown target (duration << 1)
  wire [16:0] cooldown_target_w;

  // Trigger condition
  wire trigger_w;

  // Output registers
  logic signed [15:0] out_a_r;
  logic signed [15:0] out_b_r;

  //==========================================================================
  // Control Signal Extraction
  //==========================================================================

  assign arm_w       = control[0][31];
  assign reset_cmd_w = control[0][30];

  //==========================================================================
  // RESET Edge Detection (high-to-low transition)
  //==========================================================================

  always_ff @(posedge clk) begin
    if (reset) begin
      reset_cmd_prev_r <= 1'b0;
    end else begin
      reset_cmd_prev_r <= reset_cmd_w;
    end
  end

  // High-to-low transition: previous was 1, current is 0
  assign reset_edge_w = reset_cmd_prev_r & ~reset_cmd_w;

  //==========================================================================
  // Cooldown Target Calculation
  //==========================================================================

  // duration * 2 = duration << 1 (17-bit result, no overflow)
  assign cooldown_target_w = {duration_r, 1'b0};

  //==========================================================================
  // Trigger Condition
  //==========================================================================

  // Strict greater-than comparison (signed)
  assign trigger_w = (inputa > threshold_v_r);

  //==========================================================================
  // Output Wire Assignments
  //==========================================================================

  // Drive outputs based on ARM and registered values
  assign outputa = arm_w ? out_a_r : 16'sd0;
  assign outputb = arm_w ? out_b_r : 16'sd0;
  assign outputc = 16'sd0;  // Unused on Moku:Go
  assign outputd = 16'sd0;  // Not available on Moku:Go

  //==========================================================================
  // Status Register Assignment
  //==========================================================================

  assign status[0] = {27'b0, state_r};

  // Tie unused status registers to zero
  assign status[1]  = 32'b0;
  assign status[2]  = 32'b0;
  assign status[3]  = 32'b0;
  assign status[4]  = 32'b0;
  assign status[5]  = 32'b0;
  assign status[6]  = 32'b0;
  assign status[7]  = 32'b0;
  assign status[8]  = 32'b0;
  assign status[9]  = 32'b0;
  assign status[10] = 32'b0;
  assign status[11] = 32'b0;
  assign status[12] = 32'b0;
  assign status[13] = 32'b0;
  assign status[14] = 32'b0;
  assign status[15] = 32'b0;

  //==========================================================================
  // FSM, Parameter Latching, Counter, and Output Logic
  //==========================================================================

  always_ff @(posedge clk) begin
    if (reset) begin
      // System reset: Initialize to S_RESET state
      state_r          <= S_RESET;
      cycle_count_r    <= 17'd0;
      trigger_out_v_r  <= 16'sd0;
      intensity_out_v_r <= 16'sd0;
      threshold_v_r    <= 16'sd0;
      duration_r       <= 16'd0;
      out_a_r          <= 16'sd0;
      out_b_r          <= 16'sd0;

    end else if (reset_edge_w) begin
      // RESET command (high-to-low edge): Latch parameters, go to S_RESET
      state_r          <= S_RESET;
      cycle_count_r    <= 17'd0;
      trigger_out_v_r  <= $signed(control[1][15:0]);
      intensity_out_v_r <= $signed(control[2][15:0]);
      threshold_v_r    <= $signed(control[3][15:0]);
      duration_r       <= control[4][15:0];
      out_a_r          <= 16'sd0;
      out_b_r          <= 16'sd0;

    end else begin
      // Normal FSM operation
      case (state_r)

        S_RESET: begin
          // Transition immediately to S_IDLE
          state_r       <= S_IDLE;
          cycle_count_r <= 17'd0;
          out_a_r       <= 16'sd0;
          out_b_r       <= 16'sd0;
        end

        S_IDLE: begin
          // Wait for trigger condition (inputa > threshold_v)
          out_a_r <= 16'sd0;
          out_b_r <= 16'sd0;
          if (trigger_w && arm_w) begin
            // Trigger detected and armed: transition to S_FIRE
            state_r       <= S_FIRE;
            cycle_count_r <= 17'd1;  // First cycle of Fire state
            out_a_r       <= trigger_out_v_r;
            out_b_r       <= intensity_out_v_r;
          end
        end

        S_FIRE: begin
          // Drive outputs for 'duration' cycles
          out_a_r <= trigger_out_v_r;
          out_b_r <= intensity_out_v_r;

          if (cycle_count_r >= {1'b0, duration_r}) begin
            // Fire duration complete: transition to S_COOL
            state_r       <= S_COOL;
            cycle_count_r <= 17'd1;  // First cycle of Cool state
            out_a_r       <= 16'sd0;
            out_b_r       <= 16'sd0;
          end else begin
            cycle_count_r <= cycle_count_r + 17'd1;
          end
        end

        S_COOL: begin
          // Zero outputs for 'duration*2' cycles
          out_a_r <= 16'sd0;
          out_b_r <= 16'sd0;

          if (cycle_count_r >= cooldown_target_w) begin
            // Cooldown complete: transition to S_FINI
            state_r       <= S_FINI;
            cycle_count_r <= 17'd0;
          end else begin
            cycle_count_r <= cycle_count_r + 17'd1;
          end
        end

        S_FINI: begin
          // Hold zero outputs indefinitely until RESET
          out_a_r <= 16'sd0;
          out_b_r <= 16'sd0;
          // Remain in S_FINI (reset_edge_w will exit this state)
        end

        default: begin
          // Safety: go to S_RESET on unknown state
          state_r       <= S_RESET;
          cycle_count_r <= 17'd0;
          out_a_r       <= 16'sd0;
          out_b_r       <= 16'sd0;
        end

      endcase
    end
  end

endmodule

