use core::result;
use i2c;
use clock;
use csr;

type Result<T> = result::Result<T, &'static str>;

const BUSNO: u8 = 0;
const ADDRESS: u8 = 0x68;

#[cfg(soc_platform = "kc705")]
fn pca9548_select(channel: u8) -> Result<()> {
    i2c::start(BUSNO);
    if !i2c::write(BUSNO, (0x74 << 1)) {
        return Err("PCA9548 failed to ack write address")
    }
    if !i2c::write(BUSNO, 1 << channel) {
        return Err("PCA9548 failed to ack control word")
    }
    i2c::stop(BUSNO);
    Ok(())
}

fn reset(en: bool) {
    unsafe {
        csr::si5324_rst_n::out_write(if en { 0 } else { 1 })
    }
}

// NOTE: the logical parameters DO NOT MAP to physical values written
// into registers. They have to be mapped; see the datasheet.
// DSPLLsim reports the logical parameters in the design summary, not
// the physical register values.
pub struct FrequencySettings {
    pub n1_hs: u8,
    pub nc1_ls: u32,
    pub n2_hs: u8,
    pub n2_ls: u32,
    pub n31: u32,
    pub n32: u32,
    pub bwsel: u8
}

fn map_frequency_settings(settings: &FrequencySettings) -> Result<FrequencySettings> {
    if settings.nc1_ls != 0 && (settings.nc1_ls % 2) == 1 {
        return Err("NC1_LS must be 0 or even")
    }
    if settings.nc1_ls > (1 << 20) {
        return Err("NC1_LS is too high")
    }
    if (settings.n2_ls % 2) == 1 {
        return Err("N2_LS must be even")
    }
    if settings.n2_ls > (1 << 20) {
        return Err("N2_LS is too high")
    }
    if settings.n31 > (1 << 19) {
        return Err("N31 is too high")
    }
    if settings.n32 > (1 << 19) {
        return Err("N32 is too high")
    }
    let r = FrequencySettings {
        n1_hs: match settings.n1_hs {
            4  => 0b000,
            5  => 0b001,
            6  => 0b010,
            7  => 0b011,
            8  => 0b100,
            9  => 0b101,
            10 => 0b110,
            11 => 0b111,
            _  => return Err("N1_HS has an invalid value")
        },
        nc1_ls: settings.nc1_ls - 1,
        n2_hs: match settings.n2_hs {
            4  => 0b000,
            5  => 0b001,
            6  => 0b010,
            7  => 0b011,
            8  => 0b100,
            9  => 0b101,
            10 => 0b110,
            11 => 0b111,
            _  => return Err("N2_HS has an invalid value")
        },
        n2_ls: settings.n2_ls - 1,
        n31: settings.n31 - 1,
        n32: settings.n32 - 1,
        bwsel: settings.bwsel
    };
    Ok(r)
}

fn write(reg: u8, val: u8) -> Result<()> {
    i2c::start(BUSNO);
    if !i2c::write(BUSNO, (ADDRESS << 1)) {
        return Err("Si5324 failed to ack write address")
    }
    if !i2c::write(BUSNO, reg) {
        return Err("Si5324 failed to ack register")
    }
    if !i2c::write(BUSNO, val) {
        return Err("Si5324 failed to ack value")
    }
    i2c::stop(BUSNO);
    Ok(())
}

fn read(reg: u8) -> Result<u8> {
    i2c::start(BUSNO);
    if !i2c::write(BUSNO, (ADDRESS << 1)) {
        return Err("Si5324 failed to ack write address")
    }
    if !i2c::write(BUSNO, reg) {
        return Err("Si5324 failed to ack register")
    }
    i2c::restart(BUSNO);
    if !i2c::write(BUSNO, (ADDRESS << 1) | 1) {
        return Err("Si5324 failed to ack read address")
    }
    let val = i2c::read(BUSNO, false);
    i2c::stop(BUSNO);
    Ok(val)
}

fn ident() -> Result<u16> {
    Ok(((read(134)? as u16) << 8) | (read(135)? as u16))
}

fn has_xtal() -> Result<bool> {
    Ok((read(129)? & 0x01) == 0)  // LOSX_INT=0
}

fn has_clkin2() -> Result<bool> {
    Ok((read(129)? & 0x04) == 0)  // LOS2_INT=0
}

fn locked() -> Result<bool> {
    Ok((read(130)? & 0x01) == 0)  // LOL_INT=0
}

fn monitor_lock() -> Result<()> {
    let t = clock::get_ms();
    while !locked()? {
        // Yes, lock can be really slow.
        if clock::get_ms() > t + 20000 {
            return Err("Si5324 lock timeout");
        }
    }
    info!("Si5324 is locked");
    Ok(())
}

pub fn setup(settings: &FrequencySettings) -> Result<()> {
    let s = map_frequency_settings(settings)?;

    reset(true);
    clock::spin_us(1_000);
    reset(false);
    clock::spin_us(10_000);

    #[cfg(soc_platform = "kc705")]
    pca9548_select(7)?;

    if ident()? != 0x0182 {
        return Err("Si5324 does not have expected product number");
    }

    write(0,   read(0)? | 0x40)?;                         // FREE_RUN=1
    write(2,   (read(2)? & 0x0f) | (s.bwsel << 4))?;
    write(21,  read(21)? & 0xfe)?;                        // CKSEL_PIN=0
    write(3,   (read(3)? & 0x3f) | (0b01 << 6) | 0x10)?;  // CKSEL_REG=b01 SQ_ICAL=1
    write(4,   (read(4)? & 0x3f) | (0b00 << 6))?;         // AUTOSEL_REG=b00
    write(6,   (read(6)? & 0xc0) | 0b001111)?;            // SFOUT2_REG=b001 SFOUT1_REG=b111
    write(25,  (s.n1_hs  << 5 ) as u8)?;
    write(31,  (s.nc1_ls >> 16) as u8)?;
    write(32,  (s.nc1_ls >> 8 ) as u8)?;
    write(33,  (s.nc1_ls)       as u8)?;
    write(40,  (s.n2_hs  << 5 ) as u8 | (s.n2_ls  >> 16) as u8)?;
    write(41,  (s.n2_ls  >> 8 ) as u8)?;
    write(42,  (s.n2_ls)        as u8)?;
    write(43,  (s.n31    >> 16) as u8)?;
    write(44,  (s.n31    >> 8)  as u8)?;
    write(45,  (s.n31)          as u8)?;
    write(46,  (s.n32    >> 16) as u8)?;
    write(47,  (s.n32    >> 8)  as u8)?;
    write(48,  (s.n32)          as u8)?;
    write(137, read(137)? | 0x01)?;                       // FASTLOCK=1
    write(136, read(136)? | 0x40)?;                       // ICAL=1

    if !has_xtal()? {
        return Err("Si5324 misses XA/XB signal");
    }
    if !has_clkin2()? {
        return Err("Si5324 misses CLKIN2 signal");
    }
    monitor_lock()?;

    Ok(())
}

pub fn select_ext_input(external: bool) -> Result<()> {
    if external {
        write(3,   (read(3)? & 0x3f) | (0b00 << 6))?;  // CKSEL_REG=b00
    } else {
        write(3,   (read(3)? & 0x3f) | (0b01 << 6))?;  // CKSEL_REG=b01
    }
    monitor_lock()?;
    Ok(())
}
